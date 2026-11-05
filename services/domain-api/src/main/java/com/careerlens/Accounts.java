package com.careerlens;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import java.util.function.Supplier;

@Service
public class Accounts {
    public record Actor(String id, String username, String role) {}
    private final JdbcTemplate db; private final TransactionTemplate tx;
    private final BCryptPasswordEncoder passwords = new BCryptPasswordEncoder(12);
    private final JwtEncoder encoder; private final JwtDecoder decoder;
    private final String adminName, adminPassword;
    public Accounts(JdbcTemplate db, TransactionTemplate tx, @Value("${careerlens.jwt-secret}") String secret,
                    @Value("${careerlens.admin-username}") String adminName, @Value("${careerlens.admin-password}") String adminPassword) {
        if (secret.getBytes(StandardCharsets.UTF_8).length < 32) throw new IllegalStateException("Configure JWT_SECRET with at least 32 bytes");
        this.db=db; this.tx=tx; this.adminName=adminName.toLowerCase(Locale.ROOT); this.adminPassword=adminPassword;
        byte[] key=secret.getBytes(StandardCharsets.UTF_8);
        encoder=new NimbusJwtEncoder(new ImmutableSecret<>(key));
        decoder=NimbusJwtDecoder.withSecretKey(new SecretKeySpec(key,"HmacSHA256")).macAlgorithm(MacAlgorithm.HS256).build();
    }
    @PostConstruct void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS app_users(id VARCHAR(36) PRIMARY KEY, username VARCHAR(40) UNIQUE NOT NULL, password_hash VARCHAR(100) NOT NULL, role VARCHAR(10) NOT NULL, credits BIGINT NOT NULL CHECK(credits>=0), created_at VARCHAR(40) NOT NULL)");
        db.execute("CREATE TABLE IF NOT EXISTS app_settings(id INT PRIMARY KEY, commission_bps INT NOT NULL CHECK(commission_bps BETWEEN 0 AND 10000))");
        db.execute("CREATE TABLE IF NOT EXISTS recharges(id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, amount_cents BIGINT NOT NULL, credits BIGINT NOT NULL, commission_bps INT NOT NULL, fee_cents BIGINT NOT NULL, status VARCHAR(30) NOT NULL, idempotency_key VARCHAR(36) NOT NULL, created_at VARCHAR(40) NOT NULL, paid_at VARCHAR(40), UNIQUE(user_id,idempotency_key), FOREIGN KEY(user_id) REFERENCES app_users(id))");
        db.execute("CREATE TABLE IF NOT EXISTS analysis_runs(id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, status VARCHAR(20) NOT NULL, created_at VARCHAR(40) NOT NULL, FOREIGN KEY(user_id) REFERENCES app_users(id))");
        db.execute("CREATE TABLE IF NOT EXISTS quota_adjustments(id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, actor_id VARCHAR(36) NOT NULL, delta BIGINT NOT NULL, reason VARCHAR(200) NOT NULL, created_at VARCHAR(40) NOT NULL)");
        if (db.queryForObject("SELECT COUNT(*) FROM app_settings",Integer.class)==0) db.update("INSERT INTO app_settings VALUES(1,1000)");
        if (!adminPassword.isEmpty() && db.queryForObject("SELECT COUNT(*) FROM app_users WHERE username=?",Integer.class,adminName)==0) {
            validateCredentials(adminName,adminPassword);
            db.update("INSERT INTO app_users VALUES(?,?,?,?,?,?)",UUID.randomUUID().toString(),adminName,passwords.encode(adminPassword),"ADMIN",1000,now());
        }
        tx.executeWithoutResult(status -> {
            db.update("UPDATE app_users u SET credits=credits+(SELECT COUNT(*) FROM analysis_runs r WHERE r.user_id=u.id AND r.status='RESERVED')");
            db.update("UPDATE analysis_runs SET status='FAILED' WHERE status='RESERVED'");
        });
    }
    private static String now() { return Instant.now().toString(); }
    static void validateCredentials(String username,String password) {
        if (username==null || !username.matches("[a-zA-Z0-9_]{3,32}") || password==null || password.length()<10 || password.getBytes(StandardCharsets.UTF_8).length>72)
            throw new ServiceFailure(400,"INVALID_INPUT");
    }
    public Map<String,Object> register(String username,String password) {
        validateCredentials(username,password); username=username.toLowerCase(Locale.ROOT);
        try { db.update("INSERT INTO app_users VALUES(?,?,?,?,?,?)",UUID.randomUUID().toString(),username,passwords.encode(password),"USER",10,now()); }
        catch (org.springframework.dao.DuplicateKeyException error) { throw new ServiceFailure(409,"USERNAME_EXISTS"); }
        return login(username,password);
    }
    public Map<String,Object> login(String username,String password) {
        validateCredentials(username,password);
        var rows=db.queryForList("SELECT * FROM app_users WHERE username=?",username.toLowerCase(Locale.ROOT));
        String hash=rows.isEmpty()?"$2a$12$R9h/cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jWMUW":(String)rows.getFirst().get("PASSWORD_HASH");
        if (!passwords.matches(password,hash) || rows.isEmpty()) throw new ServiceFailure(401,"INVALID_CREDENTIALS");
        var row=rows.getFirst(); var expiry=Instant.now().plusSeconds(3600);
        var claims=JwtClaimsSet.builder().issuer("careerlens").subject((String)row.get("ID")).issuedAt(Instant.now()).expiresAt(expiry).claim("aud",List.of("careerlens-web")).build();
        String token=encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(),claims)).getTokenValue();
        return Map.of("token",token,"expiresAt",expiry.toString(),"user",user(row));
    }
    public Actor authenticate(String token) {
        try {
            var jwt=decoder.decode(token);
            if (!"careerlens".equals(jwt.getClaimAsString("iss")) || !jwt.getAudience().contains("careerlens-web")) throw new IllegalArgumentException();
            var row=db.queryForMap("SELECT id,username,role FROM app_users WHERE id=?",jwt.getSubject());
            return new Actor((String)row.get("ID"),(String)row.get("USERNAME"),(String)row.get("ROLE"));
        } catch(Exception error) { throw new ServiceFailure(401,"AUTH_REQUIRED"); }
    }
    private Map<String,Object> user(Map<String,Object> row) { return Map.of("id",row.get("ID"),"username",row.get("USERNAME"),"role",row.get("ROLE"),"credits",row.get("CREDITS"),"createdAt",row.get("CREATED_AT")); }
    public Map<String,Object> account(Actor actor) {
        var analyses=db.queryForList("SELECT id,status,created_at FROM analysis_runs WHERE user_id=? ORDER BY created_at DESC LIMIT 20",actor.id()).stream()
            .map(r -> Map.of("id",r.get("ID"),"status",r.get("STATUS"),"createdAt",r.get("CREATED_AT"))).toList();
        var orders=db.queryForList("SELECT * FROM recharges WHERE user_id=? ORDER BY created_at DESC LIMIT 50",actor.id()).stream().map(this::recharge).toList();
        return Map.of("user",user(db.queryForMap("SELECT * FROM app_users WHERE id=?",actor.id())),"recharges",orders,"analyses",analyses);
    }
    public List<Map<String,Object>> users() { return db.queryForList("SELECT * FROM app_users ORDER BY created_at DESC LIMIT 200").stream().map(this::user).toList(); }
    private Map<String,Object> recharge(Map<String,Object> r) {
        var item=new LinkedHashMap<String,Object>();
        for (String[] pair:new String[][]{{"ID","id"},{"USER_ID","userId"},{"USERNAME","username"},{"AMOUNT_CENTS","amountCents"},{"CREDITS","credits"},{"COMMISSION_BPS","commissionBps"},{"FEE_CENTS","feeCents"},{"STATUS","status"},{"CREATED_AT","createdAt"},{"PAID_AT","paidAt"}}) if(r.containsKey(pair[0])) item.put(pair[1],r.get(pair[0]));
        return item;
    }
    public List<Map<String,Object>> recharges(Actor actor) {
        String query="SELECT r.*,u.username FROM recharges r JOIN app_users u ON u.id=r.user_id";
        var rows=actor.role().equals("ADMIN")?db.queryForList(query+" ORDER BY r.created_at DESC LIMIT 200"):db.queryForList(query+" WHERE r.user_id=? ORDER BY r.created_at DESC LIMIT 50",actor.id());
        return rows.stream().map(this::recharge).toList();
    }
    public Map<String,Object> createRecharge(Actor actor,long amount,String key) {
        if(amount<100 || amount>1000000 || amount%100!=0) throw new ServiceFailure(400,"INVALID_INPUT");
        try { UUID.fromString(key); } catch(Exception e) { throw new ServiceFailure(400,"INVALID_INPUT"); }
        return tx.execute(status -> {
            db.queryForObject("SELECT credits FROM app_users WHERE id=? FOR UPDATE",Long.class,actor.id());
            var existing=db.queryForList("SELECT * FROM recharges WHERE user_id=? AND idempotency_key=?",actor.id(),key);
            if(!existing.isEmpty()) { if(((Number)existing.getFirst().get("AMOUNT_CENTS")).longValue()!=amount) throw new ServiceFailure(409,"IDEMPOTENCY_CONFLICT"); return recharge(existing.getFirst()); }
            int bps=db.queryForObject("SELECT commission_bps FROM app_settings WHERE id=1",Integer.class);
            String id=UUID.randomUUID().toString();
            db.update("INSERT INTO recharges VALUES(?,?,?,?,?,?,?,?,?,NULL)",id,actor.id(),amount,amount/10,bps,(amount*bps+5000)/10000,"PENDING",key,now());
            return recharge(db.queryForMap("SELECT * FROM recharges WHERE id=?",id));
        });
    }
    public Map<String,Object> confirm(Actor actor,String id) {
        return tx.execute(status -> {
            var rows=db.queryForList("SELECT * FROM recharges WHERE id=? AND user_id=? FOR UPDATE",id,actor.id());
            if(rows.isEmpty()) throw new ServiceFailure(404,"NOT_FOUND");
            var row=rows.getFirst();
            if("PENDING".equals(row.get("STATUS"))) {
                db.update("UPDATE app_users SET credits=credits+? WHERE id=?",row.get("CREDITS"),actor.id());
                db.update("UPDATE recharges SET status='SIMULATED_PAID',paid_at=? WHERE id=?",now(),id);
            }
            return recharge(db.queryForMap("SELECT * FROM recharges WHERE id=?",id));
        });
    }
    public Map<String,Object> settings() { return Map.of("commissionBps",db.queryForObject("SELECT commission_bps FROM app_settings WHERE id=1",Integer.class),"creditsPerYuan",10,"analysisCost",1,"paymentMode","SIMULATED"); }
    public Map<String,Object> settings(int bps) { if(bps<0 || bps>10000) throw new ServiceFailure(400,"INVALID_INPUT"); db.update("UPDATE app_settings SET commission_bps=? WHERE id=1",bps); return settings(); }
    public Map<String,Object> overview() { return Map.of("users",db.queryForObject("SELECT COUNT(*) FROM app_users",Long.class),"availableCredits",db.queryForObject("SELECT COALESCE(SUM(credits),0) FROM app_users",Long.class),"successfulAnalyses",db.queryForObject("SELECT COUNT(*) FROM analysis_runs WHERE status='SUCCEEDED'",Long.class),"simulatedRevenueCents",db.queryForObject("SELECT COALESCE(SUM(amount_cents),0) FROM recharges WHERE status='SIMULATED_PAID'",Long.class),"simulatedFeeCents",db.queryForObject("SELECT COALESCE(SUM(fee_cents),0) FROM recharges WHERE status='SIMULATED_PAID'",Long.class)); }
    public Map<String,Object> adjust(Actor admin,String id,long delta,String reason) {
        if(delta==0 || delta < -1000000 || delta > 1000000 || reason==null || reason.isBlank() || reason.length()>200) throw new ServiceFailure(400,"INVALID_INPUT");
        return tx.execute(status -> {
            if(db.update("UPDATE app_users SET credits=credits+? WHERE id=? AND credits+?>=0",delta,id,delta)!=1) throw new ServiceFailure(409,"QUOTA_CONFLICT");
            db.update("INSERT INTO quota_adjustments VALUES(?,?,?,?,?,?)",UUID.randomUUID().toString(),id,admin.id(),delta,reason,now());
            return user(db.queryForMap("SELECT * FROM app_users WHERE id=?",id));
        });
    }
    public <T> T analysis(Actor actor,String trace,Supplier<T> work) {
        tx.executeWithoutResult(status -> {
            if(db.update("UPDATE app_users SET credits=credits-1 WHERE id=? AND credits>=1",actor.id())!=1) throw new ServiceFailure(402,"QUOTA_EXHAUSTED");
            db.update("INSERT INTO analysis_runs VALUES(?,?,?,?)",trace,actor.id(),"RESERVED",now());
        });
        try { T result=work.get(); db.update("UPDATE analysis_runs SET status='SUCCEEDED' WHERE id=?",trace); return result; }
        catch(RuntimeException error) { tx.executeWithoutResult(status -> { if(db.update("UPDATE analysis_runs SET status='FAILED' WHERE id=? AND status='RESERVED'",trace)==1) db.update("UPDATE app_users SET credits=credits+1 WHERE id=?",actor.id()); }); throw error; }
    }
}
