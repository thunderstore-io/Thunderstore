import React, { PropsWithChildren, useContext, useState } from "react";
import { MarkdownPreviewProvider } from "./MarkdownPreviewContext";
import { WikiPageUpsertRequest } from "../../api";
import { useOnBeforeUnload } from "../../state/OnBeforeUnload";

type EditorOptions = {
    titleMaxLength: number;
    markdownMaxLength: number;
};

export type WikiEditErrors = {
    title: string[];
    markdown: string[];
    other: string[];
};

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
    errors: WikiEditErrors;
    setErrors: (errors: WikiEditErrors) => void;
    options: EditorOptions;
    setMarkdown: (markdown: string) => void;
    setTitle: (title: string) => void;
    clearCache: () => void;
}

export interface WikiEditContextProviderProps {
    pkg: {
        namespace: string;
        name: string;
    };
    page: WikiPageUpsertRequest | null;
    options: EditorOptions;
}

const useStoredState = (
    enabled: boolean,
    storageKey: string,
    defaultVal: string
): [() => string, (val: string) => string, () => void] => {
    if (enabled) {
        return [
            () => {
                return localStorage.getItem(storageKey) ?? defaultVal;
            },
            (val: string) => {
                localStorage.setItem(storageKey, val);
                return val;
            },
            () => localStorage.removeItem(storageKey),
        ];
    } else {
        return [() => defaultVal, (val: string) => val, () => undefined];
    }
};

export const WikiEditContextProvider: React.FC<
    PropsWithChildren<WikiEditContextProviderProps>
> = ({ children, page, pkg, options }) => {
    const [title, setTitle] = useState<string>(page?.title ?? "");
    const [errors, setErrors] = useState<WikiEditErrors>({
        title: [],
        markdown: [],
        other: [],
    });
    const [
        getStoredMarkdown,
        setStoredMarkdown,
        clearStoredMarkdown,
    ] = useStoredState(
        !page,
        "legacy.wikiEditor.newPageMarkdown",
        page?.markdown_content ?? "# New page"
    );
    const [markdown, setMarkdown] = useState<string>(getStoredMarkdown);
    const _setMarkdown = (val: string) => setMarkdown(setStoredMarkdown(val));

    useOnBeforeUnload(!!page && page.markdown_content != markdown);

    return (
        <WikiEditContext.Provider
            value={{
                page: { id: page?.id, title, markdown_content: markdown },
                package: pkg,
                options: options,
                errors,
                setErrors,
                setMarkdown: _setMarkdown,
                clearCache: clearStoredMarkdown,
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
