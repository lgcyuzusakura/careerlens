package com.careerlens;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;

@RestController
public class DocumentController {
    public record DocumentInput(@NotNull @Size(min=1,max=160) String filename,@NotNull @Size(min=1,max=2796204) String contentBase64,@NotNull @Pattern(regexp="resume|jd") String target) {}
    private final ExtractionClient client;
    public DocumentController(ExtractionClient client) { this.client=client; }
    @PostMapping("/api/v1/documents/text") public Models.Envelope<?> extract(@Valid @RequestBody DocumentInput input,@RequestAttribute("traceId") String trace) {
        return Models.Envelope.ok(client.document(input,trace));
    }
}
