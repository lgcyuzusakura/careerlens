package com.careerlens;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(ApiController.class)
@Import(ScorePolicy.class)
class ApiTest {
    @Autowired MockMvc mvc;
    @MockitoBean ExtractionClient client;
    @Test void templatesHaveEnvelopeAndTrace() throws Exception { mvc.perform(get("/api/v1/job-templates")).andExpect(status().isOk()).andExpect(jsonPath("$.code").value("OK")).andExpect(jsonPath("$.data.items.length()").value(2)).andExpect(header().exists("X-Trace-Id")); }
    @Test void rejectsUnknownFields() throws Exception { mvc.perform(post("/api/v1/matches").contentType("application/json").content("{\"resumeText\":\"abcdefghijklmnopqrst\",\"jdText\":\"Java skills\",\"unknown\":true}")).andExpect(status().isBadRequest()); }
    @Test void rejectsBlankText() throws Exception { mvc.perform(post("/api/v1/matches").contentType("application/json").content("{\"resumeText\":\" \",\"jdText\":\"Java skills\"}")).andExpect(status().isBadRequest()); }
}
