import { sleep } from "./utils";

export async function retry<T>(
    attempts: number,
    fn: () => Promise<T>,
    canRetry: () => boolean,
    onError: (e: Error | unknown) => void
): Promise<T> {
    for (let retries = attempts; retries > 0; retries--) {
        if (!canRetry()) {
            throw new Error("Retries interrupted");
        }
        try {
            return await fn();
        } catch (e) {
            onError(e);
            await sleep(5000);
        }
    }
    throw new Error(`Promise failed after ${attempts} retries!`);
}
