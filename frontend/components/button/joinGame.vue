<template>
    <Button
        :loading="isSubmitting"
        label="Join Game"
        class="w-full rounded-text-input"
        :disabled="!formIsValid"
        @click="submitForm"
    />
</template>

<script setup lang="ts">
    import {
        useIsFormValid,
        useIsSubmitting,
        useSubmitForm,
    } from "vee-validate";
    import { useJoinGameForm } from "~/composeables/useJoinGameForm";

    const formIsValid = useIsFormValid();

    const { onSubmit } = useJoinGameForm();
    const isSubmitting = useIsSubmitting();

    const submitForm = useSubmitForm(onSubmit);
</script>

<style scoped>
    :deep(.p-button) {
        border-radius: 40px !important;
    }
</style>
