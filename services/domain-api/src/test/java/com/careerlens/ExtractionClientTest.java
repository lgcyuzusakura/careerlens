package com.careerlens;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.jupiter.api.Assertions.*;
import static com.careerlens.Models.*;

class ExtractionClientTest {
    private final Input input = new Input("Synthetic Java project resume", "Java requirements", new Options(false));

    private int withServer(int status, String body, int delay, java.util.function.Consumer<ExtractionClient> check) throws Exception {
        try (var listener = new ServerSocket(0, 1, java.net.InetAddress.getByName("127.0.0.1"))) {
            var failure = new AtomicReference<Throwable>();
            var requestSize = new java.util.concurrent.atomic.AtomicInteger();
            var worker = new Thread(() -> {
                try (var socket = listener.accept()) {
                    var incoming = new java.io.BufferedInputStream(socket.getInputStream());
                    var headers = new StringBuilder();
                    while (!headers.toString().endsWith("\r\n\r\n")) {
                        int next = incoming.read(); if (next < 0) throw new java.io.EOFException(); headers.append((char)next);
                    }
                    assertTrue(headers.toString().toLowerCase().contains("x-trace-id: synthetic-trace"));
                    var length = java.util.regex.Pattern.compile("(?im)^Content-Length: (\\d+)").matcher(headers);
                    assertTrue(length.find()); requestSize.set(Integer.parseInt(length.group(1)));
                    assertEquals(requestSize.get(), incoming.readNBytes(requestSize.get()).length);
                    Thread.sleep(delay);
                    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                    var stream = socket.getOutputStream();
                    stream.write(("HTTP/1.1 " + status + " Result\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: " + bytes.length + "\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
                    stream.write(bytes); stream.flush();
                } catch (Throwable error) { if (delay == 0) failure.set(error); }
            });
            worker.setDaemon(true); worker.start();
            check.accept(new ExtractionClient(new ObjectMapper(), "http://127.0.0.1:" + listener.getLocalPort(), delay == 0 ? 2000 : 100));
            worker.join(3000);
            if (failure.get() != null) throw new AssertionError(failure.get());
            return requestSize.get();
        }
    }

    @Test void preservesTraceAndParsesSuccessfulEnvelope() throws Exception {
        withServer(200, "{\"code\":\"OK\",\"msg\":\"ok\",\"data\":{\"contractVersion\":\"analysis-v1\"}}", 0,
            client -> assertEquals("analysis-v1", client.extract(input, "synthetic-trace").contractVersion()));
    }
    @Test void mapsDownstreamRateLimit() throws Exception {
        withServer(429, "private upstream details", 0, client -> assertEquals(429, assertThrows(ServiceFailure.class, () -> client.extract(input, "synthetic-trace")).status));
    }
    @Test void rejectsMalformedAndOversizedOutput() throws Exception {
        for (String body : new String[]{"invalid-json", "x".repeat(524289)})
            withServer(200, body, 0, client -> assertEquals(502, assertThrows(ServiceFailure.class, () -> client.extract(input, "synthetic-trace")).status));
    }
    @Test void enforcesRealHttpTimeout() throws Exception {
        withServer(200, "{}", 300, client -> assertEquals(504, assertThrows(ServiceFailure.class, () -> client.extract(input, "synthetic-trace")).status));
    }
    @Test void unicodeWireEncodingPreservesRequestByteBudget() throws Exception {
        int size = withServer(200, "{\"code\":\"OK\",\"msg\":\"ok\",\"data\":{\"contractVersion\":\"analysis-v1\"}}", 0,
            client -> client.extract(new Input("😀".repeat(15000) + " Java", "Java requirements", new Options(false)), "synthetic-trace"));
        assertTrue(size < 65000, "UTF-8 supplementary characters must not expand to surrogate escapes");
    }
}
