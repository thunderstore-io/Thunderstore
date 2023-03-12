import React from "react";
import { userMarkdownPreview } from "./MarkdownPreviewContext";

const LoadingSpinner = () => {
    return (
        <div
            style={{
                position: "absolute",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 32,
                top: 0,
                left: 0,
                bottom: 0,
                right: 0,
                backgroundColor: "rgba(0, 0, 0, 0.6)",
            }}
        >
            <span>
                <i className={"fas fa-sync rotate mr-3"} />
                Loading...
            </span>
        </div>
    );
};

export const MarkdownPreview: React.FC = () => {
    const context = userMarkdownPreview();

    return (
        <div style={{ height: "100%" }}>
            {context.isLoading && <LoadingSpinner />}
            <div
                className={"markdown-body"}
                dangerouslySetInnerHTML={{ __html: context.content }}
            />
        </div>
    );
};
