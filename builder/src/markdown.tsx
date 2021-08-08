import React, { useState } from "react";
import { ExperimentalApi } from "./api";
import { ProgressBar } from "./components/ProgressBar";
import { useDebounce } from "./debounce";
import * as Sentry from "@sentry/react";
import { CodeInputPanel } from "./components/CodeInputPanel";

const LOCAL_STORAGE_KEY = "legacy.markdownPreview.markdown";

interface MarkdownPreviewProps {
    markdown: string;
}
const MarkdownPreview: React.FC<MarkdownPreviewProps> = ({ markdown }) => {
    const [html, setHtml] = useState<string>("");
    const [progressClass, setProgressClass] = useState<string | null>(null);

    const renderMarkdown = () => {
        try {
            localStorage.setItem(LOCAL_STORAGE_KEY, markdown);
        } catch (e) {
            Sentry.captureException(e);
        }
        if (markdown.length > 0) {
            ExperimentalApi.renderMarkdown({ data: { markdown: markdown } })
                .then((result) => {
                    setProgressClass("bg-success");
                    setHtml(result.html);
                })
                .catch((e) => {
                    Sentry.captureException(e);
                    setProgressClass("bg-danger");
                });
        } else {
            setHtml("");
            setProgressClass("bg-success");
        }
    };

    useDebounce(
        600,
        () => {
            renderMarkdown();
        },
        [markdown],
        () => setProgressClass("bg-warning")
    );

    return (
        <div className={"card bg-light mb-2"}>
            <div className={"card-header"}>
                {progressClass !== null ? (
                    <ProgressBar className={progressClass} progress={100} />
                ) : null}
            </div>
            <div
                className={"card-body markdown-body"}
                dangerouslySetInnerHTML={{ __html: html }}
            />
        </div>
    );
};

export const MarkdownPreviewPage: React.FC = () => {
    const [markdown, setMarkdown] = useState<string>(
        localStorage.getItem(LOCAL_STORAGE_KEY) ||
            "# This is a markdown preview placeholder"
    );
    return (
        <div style={{ marginBottom: "96px" }}>
            <CodeInputPanel
                title={"Markdown Preview"}
                initial={markdown}
                onChange={setMarkdown}
                textareaStyle={{ minHeight: "400px" }}
            />
            <MarkdownPreview markdown={markdown} />
        </div>
    );
};
