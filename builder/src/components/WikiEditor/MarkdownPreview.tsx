import React from "react";
import { userMarkdownPreview } from "./MarkdownPreviewContext";
import { LoadingIndicator } from "./LoadingIndicator";

export const MarkdownPreview: React.FC = () => {
    const context = userMarkdownPreview();

    return (
        <div style={{ height: "100%" }}>
            {context.isLoading && <LoadingIndicator />}
            <div
                className={"markdown-body"}
                dangerouslySetInnerHTML={{ __html: context.content }}
            />
        </div>
    );
};
