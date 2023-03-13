import React from "react";

export interface SizeIndicatorProps {
    current: number;
    max: number;
}
export const SizeIndicator: React.FC<SizeIndicatorProps> = ({
    current,
    max,
}) => {
    const exceedsLimit = current > max;
    const closeToLimit = current > max * 0.9;
    return (
        <span
            className={
                exceedsLimit
                    ? "text-danger"
                    : closeToLimit
                    ? "text-warning"
                    : undefined
            }
        >
            {current} / {max}
        </span>
    );
};
