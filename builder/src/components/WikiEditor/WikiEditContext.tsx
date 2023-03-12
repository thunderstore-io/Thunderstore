import React, { PropsWithChildren, useContext, useState } from "react";
import { MarkdownPreviewProvider } from "./MarkdownPreviewContext";
import { WikiPageUpsertRequest } from "../../api";

export interface IWikiEditContext {
    page: {
        id?: string;
        title: string;
        markdown_content: string;
    };
    package: {
        namespace: string;
        name: string;
    };
    setMarkdown: (markdown: string) => void;
    setTitle: (title: string) => void;
}

export interface WikiEditContextProviderProps {
    pkg: {
        namespace: string;
        name: string;
    };
    page: WikiPageUpsertRequest | null;
}

export const WikiEditContextProvider: React.FC<
    PropsWithChildren<WikiEditContextProviderProps>
> = ({ children, page, pkg }) => {
    const [title, setTitle] = useState<string>(page?.title ?? "");
    const [markdown, setMarkdown] = useState<string>(
        page?.markdown_content ?? "# New page"
    );

    return (
        <WikiEditContext.Provider
            value={{
                page: { id: page?.id, title, markdown_content: markdown },
                package: pkg,
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
