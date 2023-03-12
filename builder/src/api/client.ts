import { ThunderstoreApiError } from "./error";

export class ThunderstoreApi {
    apiKey: string | null;

    constructor(apiKey: string | null) {
        this.apiKey = apiKey;
    }

    protected apiFetch = async (
        url: string,
        method: "GET" | "POST",
        body?: string
    ) => {
        const headers = new Headers({
            "Content-Type": "application/json",
        });
        if (this.apiKey) {
            headers.set("Authorization", `Session ${this.apiKey}`);
        }
        const result = await fetch(url, {
            method: method,
            headers: headers,
            body: body,
        });
        if (result.status < 200 || result.status >= 300) {
            const message = `Invalid HTTP response status: ${result.status} ${result.statusText}`;
            throw await ThunderstoreApiError.createFromResponse(
                message,
                result
            );
        }
        return result;
    };

    protected get = async (url: string, data?: object) => {
        const queryUrl = new URL(url);
        if (data) {
            for (const [key, val] of Object.entries(data)) {
                queryUrl.searchParams.set(key, val);
            }
        }
        return this.apiFetch(queryUrl.toString(), "GET");
    };

    protected post = async (url: string, data?: object) => {
        return this.apiFetch(
            url,
            "POST",
            data ? JSON.stringify(data) : undefined
        );
    };
}
