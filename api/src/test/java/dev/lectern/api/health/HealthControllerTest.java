package dev.lectern.api.health;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class HealthControllerTest {

    // Plain unit test: week-1 CI has no database. Context/integration tests
    // arrive with Testcontainers in week 2 (DESIGN §14).
    @Test
    void healthReportsOk() {
        assertEquals("ok", new HealthController().health().get("status"));
    }
}
