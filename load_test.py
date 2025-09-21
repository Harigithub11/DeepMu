from locust import HttpUser, task, between

class APITestUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def health_check(self):
        self.client.get("/health")

    @task
    def data_endpoint(self):
        self.client.get("/data?limit=100")