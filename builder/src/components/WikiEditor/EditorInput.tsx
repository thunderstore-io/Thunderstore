import React from "react";
import { useWikiEditContext } from "./WikiEditContext";

export const MarkdownEditorInput: React.FC = () => {
    const context = useWikiEditContext();

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
                value={context.page.markdown_content}
                onChange={(evt) => context.setMarkdown(evt.target.value)}
            />
        </div>
    );
};
