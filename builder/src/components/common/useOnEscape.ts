import { useEffect } from "react";

export const useOnEscape = (onEscape: () => void) => {
    const handleEvent = (event: KeyboardEvent) => {
        if (event.key === "Escape") {
            onEscape();
        }
    };
    useEffect(() => {
        document.addEventListener("keydown", handleEvent);
        return () => document.removeEventListener("keydown", handleEvent);
    }, [handleEvent]);
};
