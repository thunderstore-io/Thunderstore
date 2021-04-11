import React, { CSSProperties, useEffect, useRef, useState } from "react";
import { ExperimentalApi } from "./api";

export const UploadFileInput: React.FC = () => {
    const fileDropPlaceholderText = "Choose or drag file here";
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [fileDropStyle, setFileDropStyle] = useState<CSSProperties>({});
    const [lastTarget, setLastTarget] = useState<EventTarget | null>(null);
    const [fileDropText, setFileDropText] = useState<string>(
        fileDropPlaceholderText
    );

    const resetFileInput = () => {
        const inp = fileInputRef.current;
        const files = inp ? inp.files || [] : [];
        if (inp && files.length > 0) {
            setFileDropText(files[0] ? files[0].name : "File selected!");
        } else {
            setFileDropText(fileDropPlaceholderText);
        }
        setFileDropStyle({
            height: undefined,
            border: undefined,
            cursor: "pointer",
        });
    };
    const windowDragEnter = (e: DragEvent) => {
        setLastTarget(e.target);
        setFileDropText("Drag file here");
        setFileDropStyle({
            height: "200px",
            border: "4px solid #fff",
            cursor: "pointer",
        });
    };
    const windowDragLeave = (e: DragEvent) => {
        if (e.target === lastTarget || e.target === document) {
            resetFileInput();
        }
    };
    const windowDrop = () => resetFileInput();
    const fileChange = () => {
        resetFileInput();
    };
    const onDrop = (e: React.DragEvent) => {
        const inp = fileInputRef.current;
        if (inp) {
            inp.files = e.dataTransfer.files;
        }
        e.preventDefault();
        resetFileInput();
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

    return (
        <label
            className="btn btn-primary btn-lg btn-block"
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            style={fileDropStyle}
        >
            {fileDropText}
            <input
                type="file"
                name="newfile"
                style={{ display: "none" }}
                ref={fileInputRef}
                onChange={fileChange}
            />
        </label>
    );
};

export const UploadForm: React.FC = () => {
    ExperimentalApi.currentUser().then((res) => {
        console.log(res);
    });
    return (
        <div>
            <UploadFileInput />
        </div>
    );
};
