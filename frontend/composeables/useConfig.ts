export const useConfig = () => {
    const config = useRuntimeConfig();

    const isProduction = computed(() => config.public.env === "production");

    const baseURL = computed(() => {
        const schema = isProduction.value ? "https" : "http";
        return `${schema}://${config.public.apiHost}`;
    });

    const wsURL = computed(() => {
        const schema = isProduction.value ? "wss" : "ws";
        return `${schema}://${config.public.apiHost}`;
    });

    return {
        isProduction,
        baseURL,
        wsURL,
    };
};