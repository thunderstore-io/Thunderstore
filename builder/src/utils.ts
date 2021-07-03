import * as crypto from "crypto-js";

export function getCookie(name: string) {
    let cookieValue = null;
    if (document.cookie && document.cookie != "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i];
            if (!cookie) continue;
            cookie = cookie.trim();

            if (cookie.substring(0, name.length + 1) == name + "=") {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
                break;
            }
        }
    }
    return cookieValue;
}

export function calculateMD5(blob: Blob): Promise<string> {
    return new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const md5 = crypto.MD5(
                crypto.enc.Latin1.parse(reader.result!.toString())
            );
            resolve(md5.toString(crypto.enc.Base64));
        };
        reader.readAsBinaryString(blob);
    });
}

export function sleep(ms: number): Promise<undefined> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
