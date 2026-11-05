package com.careerlens;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;
import java.util.*;
import static com.careerlens.Models.*;

@RestController
@RequestMapping("/api/v1")
public class AccountController {
    public record Credentials(@NotNull String username,@NotNull String password) {}
    public record Recharge(@NotNull Long amountCents,@NotNull String idempotencyKey) {}
    public record Settings(@NotNull Integer commissionBps) {}
    public record Adjustment(@NotNull Long delta,@NotNull String reason) {}
    private final Accounts accounts;
    public AccountController(Accounts accounts) { this.accounts=accounts; }
    @PostMapping("/auth/register") public Envelope<?> register(@Valid @RequestBody Credentials body) { return Envelope.ok(accounts.register(body.username(),body.password())); }
    @PostMapping("/auth/login") public Envelope<?> login(@Valid @RequestBody Credentials body) { return Envelope.ok(accounts.login(body.username(),body.password())); }
    @GetMapping({"/account","/auth/me"}) public Envelope<?> account(@RequestAttribute("actor") Accounts.Actor actor) { return Envelope.ok(accounts.account(actor)); }
    @PostMapping("/recharges") public Envelope<?> recharge(@RequestAttribute("actor") Accounts.Actor actor,@Valid @RequestBody Recharge body) { return Envelope.ok(accounts.createRecharge(actor,body.amountCents(),body.idempotencyKey())); }
    @PostMapping("/recharges/{id}/simulate-confirm") public Envelope<?> confirm(@RequestAttribute("actor") Accounts.Actor actor,@PathVariable String id) { return Envelope.ok(accounts.confirm(actor,id)); }
    @GetMapping("/admin/overview") public Envelope<?> overview() { return Envelope.ok(accounts.overview()); }
    @GetMapping("/admin/users") public Envelope<?> users() { return Envelope.ok(Map.of("items",accounts.users())); }
    @GetMapping("/admin/recharges") public Envelope<?> recharges(@RequestAttribute("actor") Accounts.Actor actor) { return Envelope.ok(Map.of("items",accounts.recharges(actor))); }
    @GetMapping("/admin/settings") public Envelope<?> settings() { return Envelope.ok(accounts.settings()); }
    @PutMapping("/admin/settings") public Envelope<?> settings(@Valid @RequestBody Settings body) { return Envelope.ok(accounts.settings(body.commissionBps())); }
    @PostMapping("/admin/users/{id}/quota") public Envelope<?> adjust(@RequestAttribute("actor") Accounts.Actor actor,@PathVariable String id,@Valid @RequestBody Adjustment body) { return Envelope.ok(accounts.adjust(actor,id,body.delta(),body.reason())); }
}
