import { sleep } from "./utils";

export class PromiseThrottler {
    private readonly parallelism: number;

    private ongoing: number = 0;

    constructor(parallelism: number) {
        this.parallelism = parallelism;
    }

    private get canStartNext(): boolean {
        return this.parallelism - this.ongoing > 0;
    }

    async throttle<T>(fn: () => Promise<T>): Promise<T> {
        while (!this.canStartNext) {
            await sleep(100);
        }
        try {
            this.ongoing += 1;
            return await fn();
        } finally {
            this.ongoing -= 1;
        }
    }
}
