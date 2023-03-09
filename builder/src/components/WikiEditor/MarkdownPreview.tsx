import React from "react";
import { useMarkdownContext } from "./MarkdownContext";

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
    const context = useMarkdownContext();

    return (
        <div style={{ height: "100%" }}>
            {context.preview.isLoading && <LoadingSpinner />}
            <div
                className={"markdown-body"}
                dangerouslySetInnerHTML={{ __html: context.preview.content }}
            />
        </div>
    );
};
