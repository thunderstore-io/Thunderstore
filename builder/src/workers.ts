class WorkerCallbackHandler {
    private readonly subscriptions: Map<
        number,
        { resolve: (val: any) => void; reject: () => void }
    >;

    constructor() {
        this.subscriptions = new Map<number, any>();
    }

    public subscribe(
        messageId: number,
        callback: { resolve: (val: any) => void; reject: () => void }
    ) {
        this.subscriptions.set(messageId, callback);
    }

    onMessage = (ev: MessageEvent<any>) => {
        if (ev.data.messageId !== undefined) {
            const handler = this.subscriptions.get(ev.data.messageId);
            if (handler) {
                this.subscriptions.delete(ev.data.messageId);
                handler.resolve(ev.data.message);
            } else {
                console.error(
                    `No listener found for worker message ${ev.data.message}`
                );
            }
        } else {
            console.error(`Unknown worker response format: ${ev.data}`);
        }
    };

    onError = (ev: ErrorEvent) => {
        console.error(ev);
    };

    onMessageError = (ev: MessageEvent<any>) => {
        if (ev.data.messageId !== undefined) {
            const handler = this.subscriptions.get(ev.data.messageId);
            if (handler) {
                this.subscriptions.delete(ev.data.messageId);
                handler.reject();
            } else {
                console.error(
                    `No listener found for worker message ${ev.data.message}`
                );
            }
        } else {
            console.error(`Unknown worker response format: ${ev.data}`);
        }
    };
}

export enum Workers {
    MD5 = "static/js/workers/md5.js",
}

class WorkerManagerImpl {
    private workers: Map<string, Worker>;
    private messageId: number;
    private readonly callbackHandler: WorkerCallbackHandler;

    constructor() {
        this.workers = new Map<string, Worker>();
        this.messageId = 0;
        this.callbackHandler = new WorkerCallbackHandler();
    }

    public getOrCreateWorker(workerName: Workers): Worker {
        let worker = this.workers.get(workerName);
        if (!worker) {
            worker = new Worker(window.origin + "/" + workerName);
            worker.onmessage = this.callbackHandler.onMessage.bind(
                this.callbackHandler
            );
            worker.onerror = this.callbackHandler.onError.bind(
                this.callbackHandler
            );
            worker.onmessageerror = this.callbackHandler.onMessageError.bind(
                this.callbackHandler
            );
            this.workers.set(workerName, worker);
        }
        return worker;
    }

    public callWorker<T>(workerName: Workers, message: any): Promise<T> {
        const worker = this.getOrCreateWorker(workerName);
        const messageId = this.messageId;
        const payload = {
            message: message,
            messageId: messageId,
        };
        const result = new Promise<T>((resolve, reject) => {
            this.callbackHandler.subscribe(messageId, { resolve, reject });
        });
        this.messageId += 1;
        worker.postMessage(payload);
        return result;
    }
}

export const WorkerManager = new WorkerManagerImpl();
