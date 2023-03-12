import React, { PropsWithChildren, useContext, useState } from "react";
import { PageEditMeta } from "./Models";
import { MarkdownPreviewProvider } from "./MarkdownPreviewContext";

export interface IWikiEditContext {
    page: {
        id?: string;
        title: string;
        markdown: string;
    };
    setMarkdown: (markdown: string) => void;
    setTitle: (title: string) => void;
}

export interface WikiEditContextProvider {
    page: PageEditMeta | null;
}

export const WikiEditContextProvider: React.FC<
    PropsWithChildren<WikiEditContextProvider>
> = ({ children, page }) => {
    const [title, setTitle] = useState<string>(page?.title ?? "");
    const [markdown, setMarkdown] = useState<string>(
        page?.markdown ?? "# New page"
    );

    return (
        <WikiEditContext.Provider
            value={{
                page: { title, markdown },
                setMarkdown,
                setTitle,
            }}
        >
            <MarkdownPreviewProvider markdown={markdown}>
                {children}
            </MarkdownPreviewProvider>
        </WikiEditContext.Provider>
    );
};
export const WikiEditContext = React.createContext<
    IWikiEditContext | undefined
>(undefined);

export const useWikiEditContext = (): IWikiEditContext => {
    return useContext(WikiEditContext)!;
};
