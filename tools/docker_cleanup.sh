#!/usr/bin/env bash

set -euo pipefail

docker container prune -f
# docker image prune -f

# # ============================================================
# # CONFIGURATION
# # ============================================================

# # Container names or IDs that are explicitly important.
# KEEP_CONTAINERS=(
# )

# # Images that are explicitly important.
# KEEP_IMAGES=(
#   "nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04"
#   "pdb-image:latest"
#   "pdb-openpcdet:latest"
#   "pdb-gps:latest"
#   "pdb-ab3dmot:latest"
#   "python:3.10-slim"
# )

# # Keep ALL currently running containers automatically.
# KEEP_RUNNING_CONTAINERS=true

# # Keep untagged / <none> images because they may be build cache.
# KEEP_UNTAGGED_IMAGES=true

# # If an item listed above does not exist, abort instead of risking
# # deleting something because of a typo.
# STRICT_KEEP_REFS=false

# # Default behavior is a dry run.
# # Actually delete things only with:
# #
# #   ./docker_cleanup.sh --apply
# #
# APPLY=false

# if [[ "${1:-}" == "--apply" ]]; then
#   APPLY=true
# fi


# # ============================================================
# # STORAGE
# # ============================================================

# # Bash associative arrays work like sets.
# declare -A PROTECTED_CONTAINER_IDS=()
# declare -A PROTECTED_IMAGE_IDS=()

# # These are specifically the image IDs from KEEP_IMAGES.
# # Containers directly using one of these images will also be kept.
# declare -A EXPLICIT_KEEP_IMAGE_IDS=()


# # ============================================================
# # HELPERS
# # ============================================================

# fail() {
#   echo ">>> Docker cleanup failed" >&2
#   exit 1
# }

# on_error() {
#   fail
# }

# trap on_error ERR

# verbose() {
#   if [[ "$APPLY" != true ]]; then
#     echo "$@"
#   fi
# }


# protect_image_id() {
#   local image_id="$1"

#   [[ -z "$image_id" ]] && return

#   PROTECTED_IMAGE_IDS["$image_id"]=1
# }


# protect_container_id() {
#   local container_id="$1"
#   local image_id

#   [[ -z "$container_id" ]] && return

#   PROTECTED_CONTAINER_IDS["$container_id"]=1

#   # A protected container's image must also be protected.
#   image_id="$(
#     docker container inspect \
#       --format '{{.Image}}' \
#       "$container_id"
#   )"

#   protect_image_id "$image_id"
# }


# container_name() {
#   docker container inspect \
#     --format '{{.Name}}' \
#     "$1" |
#     sed 's#^/##'
# }


# container_image_name() {
#   docker container inspect \
#     --format '{{.Config.Image}}' \
#     "$1"
# }


# image_tags() {
#   docker image inspect \
#     "$1" \
#     --format '{{range .RepoTags}}{{println .}}{{end}}' \
#     2>/dev/null |
#     tr '\n' ' '
# }


# # ============================================================
# # RESOLVE EXPLICIT KEEP IMAGES
# # ============================================================

# verbose ">>> Resolving KEEP_IMAGES..."

# for image in "${KEEP_IMAGES[@]}"; do

#   image_id="$(
#     docker image inspect \
#       "$image" \
#       --format '{{.Id}}' \
#       2>/dev/null || true
#   )"

#   if [[ -z "$image_id" ]]; then
#     verbose "WARNING: KEEP image does not exist: $image"

#     if [[ "$STRICT_KEEP_REFS" == true ]]; then
#       verbose "Aborting for safety."
#       fail
#     fi

#     continue
#   fi

#   verbose "KEEP IMAGE: $image"
#   verbose "            $image_id"

#   PROTECTED_IMAGE_IDS["$image_id"]=1
#   EXPLICIT_KEEP_IMAGE_IDS["$image_id"]=1

# done


# # ============================================================
# # RESOLVE EXPLICIT KEEP CONTAINERS
# # ============================================================

# verbose
# verbose ">>> Resolving KEEP_CONTAINERS..."

# for container in "${KEEP_CONTAINERS[@]}"; do

#   container_id="$(
#     docker container inspect \
#       "$container" \
#       --format '{{.Id}}' \
#       2>/dev/null || true
#   )"

#   if [[ -z "$container_id" ]]; then
#     verbose "WARNING: KEEP container does not exist: $container"

#     if [[ "$STRICT_KEEP_REFS" == true ]]; then
#       verbose "Aborting for safety."
#       fail
#     fi

#     continue
#   fi

#   verbose "KEEP CONTAINER: $(container_name "$container_id")"

#   protect_container_id "$container_id"

# done


# # ============================================================
# # KEEP ALL RUNNING CONTAINERS
# # ============================================================

# if [[ "$KEEP_RUNNING_CONTAINERS" == true ]]; then

#   verbose
#   verbose ">>> Protecting currently running containers..."

#   while IFS= read -r container_id; do

#     [[ -z "$container_id" ]] && continue

#     verbose "KEEP RUNNING: $(container_name "$container_id")"

#     protect_container_id "$container_id"

#   done < <(docker ps -q)

# fi


# # ============================================================
# # KEEP CONTAINERS DIRECTLY USING KEEP_IMAGES
# # ============================================================

# verbose
# verbose ">>> Protecting containers associated with KEEP_IMAGES..."

# while IFS= read -r container_id; do

#   [[ -z "$container_id" ]] && continue

#   image_id="$(
#     docker container inspect \
#       --format '{{.Image}}' \
#       "$container_id"
#   )"

#   if [[ -n "${EXPLICIT_KEEP_IMAGE_IDS[$image_id]+x}" ]]; then

#     verbose \
#       "KEEP RELATED: $(container_name "$container_id")" \
#       "[$(container_image_name "$container_id")]"

#     protect_container_id "$container_id"

#   fi

# done < <(docker ps -aq)


# # ============================================================
# # SHOW PROTECTED OBJECTS
# # ============================================================

# verbose
# verbose "============================================================"
# verbose "PROTECTED CONTAINERS"
# verbose "============================================================"

# for container_id in "${!PROTECTED_CONTAINER_IDS[@]}"; do

#   verbose \
#     "$(container_name "$container_id")" \
#     "[$(container_image_name "$container_id")]"

# done


# verbose
# verbose "============================================================"
# verbose "PROTECTED IMAGES"
# verbose "============================================================"

# for image_id in "${!PROTECTED_IMAGE_IDS[@]}"; do

#   tags="$(image_tags "$image_id")"

#   if [[ -z "$tags" ]]; then
#     tags="<untagged>"
#   fi

#   verbose "$image_id  $tags"

# done


# # ============================================================
# # DELETE UNRELATED CONTAINERS
# # ============================================================

# verbose
# verbose "============================================================"
# verbose "CONTAINER CLEANUP"
# verbose "============================================================"

# while IFS= read -r container_id; do

#   [[ -z "$container_id" ]] && continue

#   name="$(container_name "$container_id")"
#   image="$(container_image_name "$container_id")"

#   if [[ -n "${PROTECTED_CONTAINER_IDS[$container_id]+x}" ]]; then

#     verbose "KEEP    container: $name [$image]"
#     continue

#   fi

#   if [[ "$APPLY" == true ]]; then

#     docker rm -f "$container_id" >/dev/null

#   else

#     verbose "WOULD DELETE container: $name [$image]"

#   fi

# done < <(docker ps -aq)


# # ============================================================
# # DELETE UNRELATED IMAGES
# # ============================================================

# verbose
# verbose "============================================================"
# verbose "IMAGE CLEANUP"
# verbose "============================================================"

# while IFS= read -r image_id; do

#   [[ -z "$image_id" ]] && continue

#   # ----------------------------------------------------------
#   # Explicitly or indirectly protected image
#   # ----------------------------------------------------------

#   if [[ -n "${PROTECTED_IMAGE_IDS[$image_id]+x}" ]]; then

#     tags="$(image_tags "$image_id")"
#     [[ -z "$tags" ]] && tags="<untagged>"

#     verbose "KEEP    image: $tags"
#     continue

#   fi

#   # ----------------------------------------------------------
#   # Determine tags
#   # ----------------------------------------------------------

#   tags="$(image_tags "$image_id")"

#   # ----------------------------------------------------------
#   # Preserve untagged images as potential build cache
#   # ----------------------------------------------------------

#   if [[ -z "$tags" && "$KEEP_UNTAGGED_IMAGES" == true ]]; then

#     verbose "KEEP CACHE: $image_id"
#     continue

#   fi

#   [[ -z "$tags" ]] && tags="<untagged>"

#   # ----------------------------------------------------------
#   # Delete unrelated image
#   # ----------------------------------------------------------

#   if [[ "$APPLY" == true ]]; then

#     # --no-prune prevents Docker from automatically deleting
#     # untagged parent images.
#     docker image rm \
#       --force \
#       --no-prune \
#       "$image_id" \
#       >/dev/null

#   else

#     verbose "WOULD DELETE image: $tags"

#   fi

# done < <(
#   docker image ls \
#     -aq \
#     --no-trunc |
#     sort -u
# )


# # ============================================================
# # COMPLETE
# # ============================================================

# if [[ "$APPLY" == true ]]; then
#   echo ">>> Docker cleanup succeeded"
# else
#   verbose
#   verbose "============================================================"
#   verbose ">>> DRY RUN ONLY — nothing was deleted"
#   verbose
#   verbose "Review the output above."
#   verbose "If it looks correct, run:"
#   verbose
#   verbose "    $0 --apply"
#   verbose "============================================================"
# fi
