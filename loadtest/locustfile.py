from locust import HttpUser, task


class AnonymousUser(HttpUser):
    @task
    def index(self):
        self.client.get("/")
