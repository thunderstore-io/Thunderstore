import React, { useEffect, useState } from "react";
import { ExperimentalApi } from "./api";

export const MarkdownPreview: React.FC = () => {
    const [markdown, setMarkdown] = useState<string>(
        "# This is a markdown preview placeholder"
    );
    const [html, setHtml] = useState<string>("");

    useEffect(() => {
        ExperimentalApi.renderMarkdown({ data: { markdown: markdown } }).then(
            (result) => {
                setHtml(result.html);
            }
        );
    }, [markdown]);

    return (
        <div>
            <textarea
                value={markdown}
                onChange={(evt) => setMarkdown(evt.target.value)}
            />
            <div dangerouslySetInnerHTML={{ __html: html }} />
        </div>
    );
};

interface ReadmePreviewProps {}
export const ReadmePreview: React.FC<ReadmePreviewProps> = () => {
    return (
        <div className={"card bg-light mb-2"}>
            <div className={"card-header"}>README Preview</div>
            <div
                className={"card-body markdown-body"}
                dangerouslySetInnerHTML={{ __html: "" }}
            />
        </div>
    );
};
