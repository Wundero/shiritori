<template>
    <div class="timeline">
        <template v-for="(item, index) in value">
            <template>
                <div
                    :key="`${index}-opposite`"
                    class="flex flex-row justify-content-start align-items-end pt-sm"
                >
                    <slot name="opposite" :item="item" :index="index" />
                </div>
                <div
                    :key="`${index}-marker`"
                    class="flex flex-row justify-content-center align-items-center"
                >
                    <slot name="marker" :item="item" :index="index" />
                </div>
                <div
                    :key="`${index}-content`"
                    class="flex flex-row justify-content-center align-items-end pt-sm"
                >
                    <slot name="content" :item="item" :index="index" />
                </div>
            </template>
        </template>
    </div>
</template>

<script setup lang="ts">
    import { useGameStore } from "~/stores/useGameStore";
    import { components } from "~/schema";
    import type { PropType } from "vue";

    defineProps({
        value: {
            type: Array as PropType<{ label: string; value: any }[]>,
            required: true,
        },
    });

    const gameStore = useGameStore();

    const getPlayerName = (
        word: components["schemas"]["ShiritoriGameWord"]
    ) => {
        return gameStore.getPlayer(
            typeof word.playerId === "string" ? word.playerId : ""
        )?.name;
    };
</script>

<style scoped>
    .timeline {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
    }
    .pt-sm {
        padding-top: 0.1rem;
    }
</style>
