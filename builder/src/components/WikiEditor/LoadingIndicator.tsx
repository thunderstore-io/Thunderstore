export const LoadingIndicator = () => {
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
                zIndex: 1,
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
