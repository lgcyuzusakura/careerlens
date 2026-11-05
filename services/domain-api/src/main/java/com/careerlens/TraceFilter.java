package com.careerlens;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;
import java.util.UUID;

@Component
public class TraceFilter extends OncePerRequestFilter {
    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws ServletException, IOException {
        String trace = request.getHeader("X-Trace-Id");
        if (trace == null || !trace.matches("(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")) trace = UUID.randomUUID().toString();
        request.setAttribute("traceId",trace); response.setHeader("X-Trace-Id",trace); response.setHeader("Cache-Control","no-store");
        long started = System.nanoTime();
        try { chain.doFilter(request,response); }
        finally { if (request.getRequestURI().startsWith("/api/v1/")) System.out.printf("{\"service\":\"domain-api\",\"traceId\":\"%s\",\"status\":%d,\"durationMs\":%d}%n", trace,response.getStatus(),(System.nanoTime()-started)/1000000); }
    }
}
