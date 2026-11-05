package com.careerlens;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;

@Component
@ConditionalOnProperty(name="careerlens.auth-required",havingValue="true",matchIfMissing=true)
public class AuthFilter extends OncePerRequestFilter {
    private final Accounts accounts; private final ObjectMapper mapper;
    public AuthFilter(Accounts accounts,ObjectMapper mapper) { this.accounts=accounts;this.mapper=mapper; }
    @Override protected void doFilterInternal(HttpServletRequest request,HttpServletResponse response,FilterChain chain) throws ServletException,IOException {
        String path=request.getRequestURI();
        if(!path.startsWith("/api/v1/") || path.equals("/api/v1/auth/login") || path.equals("/api/v1/auth/register") || path.equals("/api/v1/job-templates")) { chain.doFilter(request,response);return; }
        try {
            String header=request.getHeader("Authorization");
            if(header==null || !header.startsWith("Bearer ") || header.length()>4096) throw new ServiceFailure(401,"AUTH_REQUIRED");
            var actor=accounts.authenticate(header.substring(7));
            if(path.startsWith("/api/v1/admin/") && !actor.role().equals("ADMIN")) throw new ServiceFailure(403,"FORBIDDEN");
            request.setAttribute("actor",actor);
        } catch(ServiceFailure error) {
            response.setStatus(error.status);response.setContentType("application/json");response.setHeader("Cache-Control","no-store");
            if(error.status==401) response.setHeader("WWW-Authenticate","Bearer");
            mapper.writeValue(response.getOutputStream(),new Models.Envelope<>(error.code,error.status==403?"需要管理员权限。":"请登录后继续。",null));return;
        }
        chain.doFilter(request,response);
    }
}
