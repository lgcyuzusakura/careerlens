package com.careerlens;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nimbusds.jose.*;
import com.nimbusds.jose.crypto.MACSigner;
import com.nimbusds.jwt.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(properties={"spring.datasource.url=jdbc:h2:mem:account-security;DB_CLOSE_DELAY=-1", "spring.datasource.password=", "careerlens.jwt-secret=synthetic-test-signing-material-at-least-32-bytes", "careerlens.admin-username=fixture_admin", "careerlens.admin-password=synthetic-admin-password"})
@AutoConfigureMockMvc
class AccountSecurityTest {
    @Autowired Accounts accounts;
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;
    @Autowired JdbcTemplate db;
    private static final String PASSWORD="synthetic-user-password";
    private String username() { return "u"+UUID.randomUUID().toString().replace("-","").substring(0,20); }
    private Map<String,Object> register() { return accounts.register(username(),PASSWORD); }
    @SuppressWarnings("unchecked") private Accounts.Actor actor(Map<String,Object> session) {
        var user=(Map<String,Object>)session.get("user");
        return new Accounts.Actor((String)user.get("id"),(String)user.get("username"),(String)user.get("role"));
    }
    @SuppressWarnings("unchecked") private long credits(Accounts.Actor actor) { return ((Number)((Map<String,Object>)accounts.account(actor).get("user")).get("credits")).longValue(); }
    private void failure(int expected,Runnable operation) { var error=assertThrows(ServiceFailure.class,operation::run); assertEquals(expected,error.status); }

    @Test void registrationNormalizesUsernameAndNeverReturnsPasswordHash() throws Exception {
        String name=username(); var session=accounts.register(name.toUpperCase(Locale.ROOT),PASSWORD); var actor=actor(session);
        assertEquals(name,actor.username()); assertEquals("USER",actor.role()); assertEquals(10,credits(actor));
        assertFalse(mapper.writeValueAsString(session).contains("password"));
        assertEquals(actor.id(),actor(accounts.login(name,PASSWORD)).id());
        failure(409,()->accounts.register(name,PASSWORD)); failure(401,()->accounts.login(name,"incorrect-synthetic-password"));
        String hash=db.queryForObject("SELECT password_hash FROM app_users WHERE id=?",String.class,actor.id());
        assertNotEquals(PASSWORD,hash); assertTrue(hash.startsWith("$2"));
    }
    @Test void freshlyIssuedTokenAuthenticatesItsOwner() {
        var session=register();
        assertEquals(actor(session).id(),accounts.authenticate((String)session.get("token")).id());
    }
    @Test void credentialsRejectUnsupportedNamesAndBcryptTruncation() {
        failure(400,()->accounts.register("ab",PASSWORD));
        failure(400,()->accounts.register(username(),"short"));
        failure(400,()->accounts.register(username(),"密".repeat(25)));
        failure(400,()->accounts.login("bad name",PASSWORD));
    }
    @Test void protectedRoutesRejectAnonymousRequestsWithTraceAndEnvelope() throws Exception {
        for(String path:List.of("/api/v1/account","/api/v1/admin/users","/api/v1/admin/recharges"))
            mvc.perform(get(path)).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.data").isEmpty()).andExpect(header().exists("X-Trace-Id")).andExpect(header().string("WWW-Authenticate","Bearer"));
        mvc.perform(post("/api/v1/matches").contentType("application/json").content("{}"))
            .andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("AUTH_REQUIRED"));
    }
    @Test void userCannotPromoteThemselvesOrReadAdminData() throws Exception {
        var session=register(); String auth="Bearer "+session.get("token");
        for(String path:List.of("/api/v1/admin/users","/api/v1/admin/recharges","/api/v1/admin/overview","/api/v1/admin/settings"))
            mvc.perform(get(path).header("Authorization",auth)).andExpect(status().isForbidden());
        mvc.perform(put("/api/v1/admin/settings").header("Authorization",auth).contentType("application/json").content("{\"commissionBps\":0}"))
            .andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/auth/register").contentType("application/json").content(mapper.writeValueAsString(Map.of("username",username(),"password",PASSWORD,"role","ADMIN"))))
            .andExpect(status().isBadRequest());
    }
    @Test void jwtRejectsTamperedExpiredAndWrongAudience() throws Exception {
        String token=(String)register().get("token"); var parsed=SignedJWT.parse(token);
        var otherKey=new SignedJWT(parsed.getHeader(),parsed.getJWTClaimsSet()); otherKey.sign(new MACSigner("different-synthetic-signing-material-32-bytes"));
        failure(401,()->accounts.authenticate(otherKey.serialize()));
        for(String kind:List.of("expired","audience")) {
            var claims=new JWTClaimsSet.Builder(parsed.getJWTClaimsSet()).issuer("careerlens").audience(kind.equals("audience")?"other-app":"careerlens-web")
                .expirationTime(Date.from(kind.equals("expired")?Instant.now().minusSeconds(300):Instant.now().plusSeconds(300))).build();
            var jwt=new SignedJWT(new JWSHeader(JWSAlgorithm.HS256),claims); jwt.sign(new MACSigner("synthetic-test-signing-material-at-least-32-bytes"));
            failure(401,()->accounts.authenticate(jwt.serialize()));
        }
    }
    @Test void rechargeCreationAndConfirmationAreIdempotentAndOwnerScoped() {
        var user=actor(register()); var stranger=actor(register()); String key=UUID.randomUUID().toString();
        var order=accounts.createRecharge(user,1000,key); String id=(String)order.get("id");
        assertEquals(id,accounts.createRecharge(user,1000,key).get("id"));
        failure(409,()->accounts.createRecharge(user,2000,key)); failure(404,()->accounts.confirm(stranger,id));
        assertTrue(accounts.recharges(stranger).stream().noneMatch(r->id.equals(r.get("id"))));
        assertEquals("SIMULATED_PAID",accounts.confirm(user,id).get("status")); accounts.confirm(user,id);
        assertEquals(110,credits(user)); assertEquals(10,credits(stranger));
    }
    @Test void concurrentPaymentConfirmationCreditsExactlyOnce() throws Exception {
        var user=actor(register()); String id=(String)accounts.createRecharge(user,1000,UUID.randomUUID().toString()).get("id");
        try(var pool=Executors.newFixedThreadPool(6)) {
            var tasks=new ArrayList<Callable<Object>>(); for(int i=0;i<6;i++) tasks.add(()->accounts.confirm(user,id));
            for(var future:pool.invokeAll(tasks)) future.get(10,TimeUnit.SECONDS);
        }
        assertEquals(110,credits(user));
    }
    @Test void commissionIsSnapshottedAndDoesNotReducePurchasedCredits() {
        var user=actor(register()); int before=((Number)accounts.settings().get("commissionBps")).intValue();
        try {
            accounts.settings(1250); var order=accounts.createRecharge(user,1000,UUID.randomUUID().toString());
            accounts.settings(2500); var paid=accounts.confirm(user,(String)order.get("id"));
            assertEquals(1250,((Number)paid.get("commissionBps")).intValue()); assertEquals(125,((Number)paid.get("feeCents")).longValue()); assertEquals(110,credits(user));
            failure(400,()->accounts.settings(-1)); failure(400,()->accounts.settings(10001));
        } finally { accounts.settings(before); }
    }
    @Test void failedAnalysisRefundsAndRecordsFailure() {
        var user=actor(register()); String trace=UUID.randomUUID().toString();
        failure(504,()->accounts.analysis(user,trace,()->{ throw new ServiceFailure(504,"UPSTREAM_TIMEOUT"); }));
        assertEquals(10,credits(user)); assertEquals("FAILED",db.queryForObject("SELECT status FROM analysis_runs WHERE id=?",String.class,trace));
        assertEquals("result",accounts.analysis(user,UUID.randomUUID().toString(),()->"result")); assertEquals(9,credits(user));
    }
    @Test void concurrentAnalysesCannotOverspendQuota() throws Exception {
        var user=actor(register()); var tasks=new ArrayList<Callable<Boolean>>();
        for(int i=0;i<14;i++) tasks.add(()->{ try { accounts.analysis(user,UUID.randomUUID().toString(),()->"result"); return true; } catch(ServiceFailure e) { assertEquals(402,e.status); return false; } });
        int success=0;
        try(var pool=Executors.newFixedThreadPool(7)) { for(var future:pool.invokeAll(tasks)) if(future.get(10,TimeUnit.SECONDS)) success++; }
        assertEquals(10,success); assertEquals(0,credits(user));
    }
    @Test void quotaAdjustmentsRejectNegativeBalancesAndRecordReason() {
        var user=actor(register()); var admin=actor(accounts.login("fixture_admin","synthetic-admin-password"));
        failure(409,()->accounts.adjust(admin,user.id(),-11,"synthetic adjustment")); assertEquals(10,credits(user));
        accounts.adjust(admin,user.id(),5,"synthetic support grant"); assertEquals(15,credits(user));
        assertEquals("synthetic support grant",db.queryForObject("SELECT reason FROM quota_adjustments WHERE user_id=?",String.class,user.id()));
        failure(400,()->accounts.adjust(admin,user.id(),1,""));
    }
}
