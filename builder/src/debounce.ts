import { DependencyList, EffectCallback, useEffect } from "react";

export const useDebounce = (
    time: number,
    effect: EffectCallback,
    deps?: DependencyList,
    onChange?: () => void
) => {
    useEffect(() => {
        if (onChange) onChange();
        const timeoutId = setTimeout(() => effect(), time);
        return () => clearTimeout(timeoutId);
    }, deps);
};
