import React from "react";
import { useMarkdownContext } from "./MarkdownContext";

export const MarkdownEditorInput: React.FC = () => {
    const context = useMarkdownContext();

    return (
        <div className={"d-flex flex-column h-100"}>
            <p>
                <a href={"https://www.markdownguide.org/basic-syntax/"}>
                    Markdown
                </a>{" "}
                syntax supported!
            </p>
            <textarea
                className={"code-input"}
                style={{ flex: 1 }}
                value={context.markdown}
                onChange={(evt) => context.setMarkdown(evt.target.value)}
            />
        </div>
    );
};
