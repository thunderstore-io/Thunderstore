import React, { CSSProperties, useEffect, useRef, useState } from "react";

interface DragDropFileInputProps {
    title: string;
    onChange?: (files: FileList) => void;
    readonly?: boolean;
}

export const DragDropFileInput: React.FC<DragDropFileInputProps> = (props) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [fileDropStyle, setFileDropStyle] = useState<CSSProperties>({});
    const [lastTarget, setLastTarget] = useState<EventTarget | null>(null);
    const [isDragging, setIsDragging] = useState<boolean>(false);

    const resetDragState = () => {
        setIsDragging(false);
        setFileDropStyle({
            height: undefined,
            border: undefined,
        });
    };
    const windowDragEnter = (e: DragEvent) => {
        setIsDragging(true);
        setLastTarget(e.target);
        if (!props.readonly) {
            setFileDropStyle({
                height: "200px",
                border: "4px solid #fff",
            });
        }
    };
    const windowDragLeave = (e: DragEvent) => {
        if (e.target === lastTarget || e.target === document) {
            resetDragState();
        }
    };
    const windowDrop = () => {
        resetDragState();
    };
    const fileChange = () => {
        if (!props.readonly) {
            const inp = fileInputRef.current;
            const files = inp?.files;
            if (props.onChange && files) {
                props.onChange(files);
            }
        }
        resetDragState();
    };
    const onDrop = (e: React.DragEvent) => {
        if (!props.readonly) {
            const inp = fileInputRef.current;
            if (inp) {
                inp.files = e.dataTransfer.files;
            }
            if (props.onChange) {
                props.onChange(e.dataTransfer.files);
            }
        }
        e.preventDefault();
        resetDragState();
    };

    useEffect(() => {
        window.addEventListener("dragenter", windowDragEnter);
        window.addEventListener("dragleave", windowDragLeave);
        window.addEventListener("drop", windowDrop);
        return () => {
            window.removeEventListener("dragenter", windowDragEnter);
            window.removeEventListener("dragleave", windowDragLeave);
            window.removeEventListener("drop", windowDrop);
        };
    });

    const extraClass = !!props.readonly ? "disabled" : "";
    const finalStyle = {
        height: fileDropStyle.height,
        border: fileDropStyle.border,
        cursor: !!props.readonly ? undefined : "pointer",
    };

    return (
        <label
            className={`btn btn-primary btn-lg btn-block ${extraClass}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            style={finalStyle}
            aria-disabled={props.readonly}
        >
            {isDragging && !props.readonly ? "Drag file here" : props.title}
            <input
                type="file"
                name="newfile"
                style={{ display: "none" }}
                ref={fileInputRef}
                onChange={fileChange}
                disabled={props.readonly}
            />
        </label>
    );
};
