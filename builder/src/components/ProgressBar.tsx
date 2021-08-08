import React from "react";
import { observer } from "mobx-react";

interface ProgressBarProps {
    className: string;
    progress: number;
}
export const ProgressBar: React.FC<ProgressBarProps> = observer(
    ({ className, progress }) => {
        return (
            <div className="progress my-2">
                <div
                    className={`progress-bar progress-bar-striped progress-bar-animated ${className}`}
                    role="progressbar"
                    aria-valuenow={progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    style={{
                        width: `${progress}%`,
                    }}
                />
            </div>
        );
    }
);
