import React, {
    PropsWithChildren,
    useCallback,
    useContext,
    useState,
} from "react";
import { ExperimentalApi } from "../../api";
import * as Sentry from "@sentry/react";
import { useDebounce } from "../../debounce";

export type PreviewStatus = {
    content: string;
    isLoading: boolean;
};

export interface MarkdownPreviewProviderProps {
    markdown: string;
}

export const MarkdownPreviewProvider: React.FC<
    PropsWithChildren<MarkdownPreviewProviderProps>
> = ({ children, markdown }) => {
    const [preview, setPreview] = useState<PreviewStatus>({
        content: "",
        isLoading: false,
    });

    const renderMarkdown = useCallback((localMarkdown) => {
        if (localMarkdown.length > 0) {
            ExperimentalApi.renderMarkdown({
                data: { markdown: localMarkdown },
            })
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
    }, []);

    useDebounce(
        600,
        () => renderMarkdown(markdown),
        [markdown],
        () => setPreview({ ...preview, isLoading: true })
    );

    return (
        <MarkdownPreviewContext.Provider value={preview}>
            {children}
        </MarkdownPreviewContext.Provider>
    );
};
export const MarkdownPreviewContext = React.createContext<
    PreviewStatus | undefined
>(undefined);

export const userMarkdownPreview = (): PreviewStatus => {
    return useContext(MarkdownPreviewContext)!;
};
