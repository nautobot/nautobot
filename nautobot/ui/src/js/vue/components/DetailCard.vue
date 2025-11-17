<template>
    <div class="card mb-4">
        <div class="card-header">
            <h5 class="card-title mb-0">{{ title }}</h5>
        </div>
        <div class="card-body">
            <slot></slot>
        </div>
    </div>
</template>

<script>
export default {
    name: 'DetailCard',
    props: {
        title: {
            type: String,
            required: true,
        },
    },
};
</script>

<style scoped>
/* Using Bootstrap's default card styling */
</style>
