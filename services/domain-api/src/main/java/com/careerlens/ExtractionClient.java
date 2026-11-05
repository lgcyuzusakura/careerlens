package com.careerlens;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import static com.careerlens.Models.*;

@Component
public class ExtractionClient {
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(1)).followRedirects(HttpClient.Redirect.NEVER).build();
    private final ObjectMapper mapper;
    private final String base;
    private final long timeout;
    public ExtractionClient(ObjectMapper mapper, @Value("${careerlens.python-url}") String base, @Value("${careerlens.python-timeout-ms}") long timeout) {
        this.mapper = mapper; this.base = base; this.timeout = timeout;
    }
    public Extraction extract(Input input, String trace) {
        try {
            var body = new ExtractionInput(input.resumeText(), input.jdText(), input.options() == null ? new Options(false) : input.options(), "analysis-v1", "skills-v1");
            var request = HttpRequest.newBuilder(URI.create(base + "/internal/v1/extractions"))
                .timeout(Duration.ofMillis(timeout)).header("Content-Type", "application/json").header("X-Trace-Id", trace)
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body))).build();
            var response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());
            if (response.body().length > 524288) throw new ServiceFailure(502, "UPSTREAM_FAILURE");
            if (response.statusCode() != 200) {
                int status = switch(response.statusCode()) { case 400,422,429,503,504 -> response.statusCode(); default -> 502; };
                throw new ServiceFailure(status, switch(status) { case 400 -> "INVALID_INPUT"; case 422 -> "UNANALYZABLE_INPUT"; case 429 -> "RATE_LIMITED"; case 503 -> "SERVICE_UNAVAILABLE"; case 504 -> "UPSTREAM_TIMEOUT"; default -> "UPSTREAM_FAILURE"; });
            }
            Envelope<Extraction> envelope = mapper.readValue(response.body(), new TypeReference<>() {});
            if (!"OK".equals(envelope.code()) || envelope.data() == null) throw new ServiceFailure(502, "UPSTREAM_FAILURE");
            return envelope.data();
        } catch (HttpTimeoutException e) { throw new ServiceFailure(504, "UPSTREAM_TIMEOUT"); }
        catch (InterruptedException e) { Thread.currentThread().interrupt(); throw new ServiceFailure(503, "SERVICE_UNAVAILABLE"); }
        catch (ServiceFailure e) { throw e; }
        catch (Exception e) { throw new ServiceFailure(502, "UPSTREAM_FAILURE"); }
    }
}
