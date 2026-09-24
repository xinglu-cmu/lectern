package dev.lectern.api.health;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class HealthControllerTest {

    // Plain unit test: CI has no database yet. Context/integration tests
    // arrive with Testcontainers in week 4, alongside auth (DESIGN §7).
    @Test
    void healthReportsOk() {
        assertEquals("ok", new HealthController().health().get("status"));
    }
}
