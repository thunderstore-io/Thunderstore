import React, { CSSProperties } from "react";

interface CodeInputPanelProps {
    title: string;
    initial: string;
    onChange: (value: string) => void;
    textareaStyle?: CSSProperties;
}
export const CodeInputPanel: React.FC<CodeInputPanelProps> = ({
    title,
    initial,
    onChange,
    children,
    textareaStyle,
}) => {
    return (
        <div className={"card bg-light mb-2"}>
            <div className={"card-header"}>{title}</div>
            <div className={"card-body"}>
                {children}
                <textarea
                    className={"code-input"}
                    style={textareaStyle}
                    value={initial}
                    onChange={(evt) => onChange(evt.target.value)}
                />
            </div>
        </div>
    );
};
