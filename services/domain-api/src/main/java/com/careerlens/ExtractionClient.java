package com.careerlens;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.net.URI;
import java.net.HttpURLConnection;
import java.net.SocketTimeoutException;
import java.util.concurrent.*;
import java.io.ByteArrayOutputStream;
import static com.careerlens.Models.*;

@Component
public class ExtractionClient {
    private static final ScheduledExecutorService DEADLINES = Executors.newSingleThreadScheduledExecutor(r -> { var thread = new Thread(r, "python-http-deadlines"); thread.setDaemon(true); return thread; });
    private final ObjectMapper mapper;
    private final String base;
    private final long timeout;
    public ExtractionClient(ObjectMapper mapper, @Value("${careerlens.python-url}") String base, @Value("${careerlens.python-timeout-ms}") long timeout) {
        this.mapper = mapper; this.base = base; this.timeout = timeout;
    }
    public Extraction extract(Input input, String trace) {
        var body = new ExtractionInput(input.resumeText(), input.jdText(), input.options() == null ? new Options(false) : input.options(), "analysis-v1", "skills-v1");
        return post("/internal/v1/extractions",body,trace,new TypeReference<Envelope<Extraction>>() {});
    }
    public java.util.Map<String,Object> document(DocumentController.DocumentInput body,String trace) {
        return post("/internal/v1/documents/text",body,trace,new TypeReference<Envelope<java.util.Map<String,Object>>>() {});
    }
    private <T> T post(String path,Object body,String trace,TypeReference<Envelope<T>> type) {
        HttpURLConnection connection = null;
        ScheduledFuture<?> deadline = null;
        long started = System.nanoTime();
        try {
            connection = (HttpURLConnection) URI.create(base + path).toURL().openConnection();
            connection.setConnectTimeout(1000); connection.setReadTimeout(Math.toIntExact(timeout));
            connection.setInstanceFollowRedirects(false); connection.setRequestMethod("POST"); connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json"); connection.setRequestProperty("X-Trace-Id", trace);
            final var active = connection;
            deadline = DEADLINES.schedule(active::disconnect, timeout, TimeUnit.MILLISECONDS);
            byte[] bytes = mapper.writer().with(com.fasterxml.jackson.core.json.JsonWriteFeature.COMBINE_UNICODE_SURROGATES_IN_UTF8).writeValueAsBytes(body); connection.setFixedLengthStreamingMode(bytes.length);
            try (var stream = connection.getOutputStream()) { stream.write(bytes); }
            int responseStatus = connection.getResponseCode();
            if (responseStatus != 200) {
                int status = switch(responseStatus) { case 400,422,429,503,504 -> responseStatus; default -> 502; };
                throw new ServiceFailure(status, switch(status) { case 400 -> "INVALID_INPUT"; case 422 -> "UNANALYZABLE_INPUT"; case 429 -> "RATE_LIMITED"; case 503 -> "SERVICE_UNAVAILABLE"; case 504 -> "UPSTREAM_TIMEOUT"; default -> "UPSTREAM_FAILURE"; });
            }
            var buffer = new ByteArrayOutputStream();
            try (var stream = connection.getInputStream()) {
                byte[] chunk = new byte[8192]; int count;
                while ((count = stream.read(chunk)) != -1) {
                    if (buffer.size() + count > 524288) throw new ServiceFailure(502, "UPSTREAM_FAILURE");
                    buffer.write(chunk,0,count);
                }
            }
            Envelope<T> envelope = mapper.readValue(buffer.toByteArray(), type);
            if (!"OK".equals(envelope.code()) || envelope.data() == null) throw new ServiceFailure(502, "UPSTREAM_FAILURE");
            return envelope.data();
        } catch (SocketTimeoutException e) { throw new ServiceFailure(504, "UPSTREAM_TIMEOUT"); }
        catch (ServiceFailure e) { throw e; }
        catch (Exception e) { throw new ServiceFailure((System.nanoTime()-started)/1000000 >= timeout ? 504 : 502, (System.nanoTime()-started)/1000000 >= timeout ? "UPSTREAM_TIMEOUT" : "UPSTREAM_FAILURE"); }
        finally { if (deadline != null) deadline.cancel(false); if (connection != null) connection.disconnect(); }
    }
}
