import React, { PropsWithChildren, useContext, useState } from "react";
import { ExperimentalApi } from "../../api";
import * as Sentry from "@sentry/react";
import { useDebounce } from "../../debounce";

export type PreviewStatus = {
    content: string;
    isLoading: boolean;
};

export interface IMarkdownContext {
    markdown: string;
    preview: PreviewStatus;
    setMarkdown: (markdown: string) => void;
}

export interface MarkdownContextProviderProps {
    initial: string;
}

export const MarkdownContextProvider: React.FC<
    PropsWithChildren<MarkdownContextProviderProps>
> = ({ children, initial }) => {
    const [markdown, setMarkdown] = useState<string>(initial);
    const [preview, setPreview] = useState<PreviewStatus>({
        content: "",
        isLoading: false,
    });

    const renderMarkdown = () => {
        if (markdown.length > 0) {
            ExperimentalApi.renderMarkdown({ data: { markdown } })
                .then((result) => {
                    setPreview({
                        ...preview,
                        content: result.html,
                        isLoading: false,
                    });
                })
                .catch((e) => {
                    Sentry.captureException(e);
                    setPreview({
                        ...preview,
                        isLoading: false,
                        content: "Failed to render preview",
                    });
                });
        } else {
            setPreview({
                ...preview,
                content: "",
                isLoading: false,
            });
        }
    };

    useDebounce(
        600,
        () => {
            renderMarkdown();
        },
        [markdown],
        () => setPreview({ ...preview, isLoading: true })
    );

    return (
        <MarkdownContext.Provider
            value={{
                markdown,
                preview,
                setMarkdown,
            }}
        >
            {children}
        </MarkdownContext.Provider>
    );
};
export const MarkdownContext = React.createContext<
    IMarkdownContext | undefined
>(undefined);

export const useMarkdownContext = (): IMarkdownContext => {
    return useContext(MarkdownContext)!;
};
