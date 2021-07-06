import { useEffect } from "react";

const onBeforeUnload = () => {
    return "You have unsaved changes, are you sure you want to exit?";
};

// This class is responsible for tracking claims on the window.onbeforeunload
// event, and setting the event handler accordingly. Centralizing the management
// is necessary to avoid components unaware of each other from unregistering
// each other's event handlers.
class OnBeforeUnloadTracker {
    private nextId: number = 0;
    private readonly subscriptions: Set<number> = new Set<number>();

    public subscribe(): number {
        const id = this.nextId;
        this.nextId += 1;
        this.subscriptions.add(id);
        if (window.onbeforeunload == null) {
            window.onbeforeunload = onBeforeUnload;
        }
        return id;
    }

    public unsubscribe(id: number) {
        this.subscriptions.delete(id);
        if (this.subscriptions.size == 0 && window.onbeforeunload !== null) {
            window.onbeforeunload = null;
        }
    }
}

export const OnBeforeUnload = new OnBeforeUnloadTracker();

export const useOnBeforeUnload = (enabled: boolean) => {
    useEffect(() => {
        if (enabled) {
            const handle = OnBeforeUnload.subscribe();
            return () => {
                OnBeforeUnload.unsubscribe(handle);
            };
        } else {
            return () => {};
        }
    }, [enabled]);
};
