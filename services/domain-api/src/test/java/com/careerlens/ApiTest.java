package com.careerlens;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(controllers=ApiController.class,properties="careerlens.auth-required=false")
@Import(ScorePolicy.class)
class ApiTest {
    @Autowired MockMvc mvc;
    @MockitoBean ExtractionClient client;
    @MockitoBean Accounts accounts;
    @Test void templatesHaveEnvelopeAndTrace() throws Exception { mvc.perform(get("/api/v1/job-templates")).andExpect(status().isOk()).andExpect(jsonPath("$.code").value("OK")).andExpect(jsonPath("$.data.items.length()").value(org.hamcrest.Matchers.greaterThanOrEqualTo(6))).andExpect(header().exists("X-Trace-Id")); }
    @Test void rejectsUnknownFields() throws Exception { mvc.perform(post("/api/v1/matches").contentType("application/json").content("{\"resumeText\":\"abcdefghijklmnopqrst\",\"jdText\":\"Java skills\",\"unknown\":true}")).andExpect(status().isBadRequest()); }
    @Test void rejectsBlankText() throws Exception { mvc.perform(post("/api/v1/matches").requestAttr("actor",new Accounts.Actor("synthetic","tester","USER")).contentType("application/json").content("{\"resumeText\":\" \",\"jdText\":\"Java skills\"}")).andExpect(status().isBadRequest()); }
    @Test void unknownResourceHasRestErrorEnvelope() throws Exception { mvc.perform(get("/api/v1/unknown")).andExpect(status().isNotFound()).andExpect(jsonPath("$.code").value("NOT_FOUND")); }
    @Test void wrongMethodHasRestErrorEnvelope() throws Exception { mvc.perform(get("/api/v1/matches")).andExpect(status().isMethodNotAllowed()).andExpect(jsonPath("$.code").value("METHOD_NOT_ALLOWED")); }
}
