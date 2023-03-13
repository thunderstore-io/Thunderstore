import React from "react";
import { useWikiEditContext } from "./WikiEditContext";
import { SizeIndicator } from "./SizeIndicator";
import { ErrorList } from "./ErrorList";

const MarkdownLengthIndicator = () => {
    const context = useWikiEditContext();
    return (
        <SizeIndicator
            current={context.page.markdown_content.length}
            max={context.options.markdownMaxLength}
        />
    );
};

export const MarkdownEditorInput: React.FC = () => {
    const context = useWikiEditContext();

    return (
        <div className={"d-flex flex-column h-100 gap-1"}>
            <span>
                <a href={"https://www.markdownguide.org/basic-syntax/"}>
                    Markdown
                </a>{" "}
                syntax supported!
            </span>
            <textarea
                className={"code-input"}
                style={{ flex: 1 }}
                value={context.page.markdown_content}
                onChange={(evt) => context.setMarkdown(evt.target.value)}
            />
            <MarkdownLengthIndicator />
            <ErrorList errors={context.errors.markdown} />
        </div>
    );
};
