import streamlit as st
from supabase import create_client
from urllib.parse import quote
from io import BytesIO
from urllib.request import urlopen
from PIL import Image
import uuid


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Catalogue Admin",
    page_icon="⚙️",
    layout="wide",
)


# =========================================================
# CONSTANTS
# =========================================================

TABLE_NAME = "leather_products"
BUCKET_NAME = "leather-images"


# =========================================================
# SUPABASE CONNECTION
# =========================================================

@st.cache_resource
def get_admin_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )


try:

    supabase = get_admin_supabase()

except Exception as e:

    st.error(
        "Supabase admin connection could not be established."
    )

    st.info(
        "Please add SUPABASE_SERVICE_ROLE_KEY "
        "to Streamlit secrets."
    )

    st.exception(e)

    st.stop()


# =========================================================
# ADMIN LOGIN
# =========================================================

def check_admin_password():

    if st.session_state.get(
        "admin_authenticated",
        False,
    ):
        return True

    st.title("🔐 Catalogue Administration")

    st.caption(
        "Restricted area for managing the leather catalogue."
    )

    password = st.text_input(
        "Admin Password",
        type="password",
        placeholder="Enter admin password",
    )

    if st.button(
        "Login",
        type="primary",
        width="stretch",
    ):

        admin_password = st.secrets.get(
            "ADMIN_PASSWORD"
        )

        if not admin_password:

            st.error(
                "ADMIN_PASSWORD is not configured "
                "in Streamlit secrets."
            )

            return False

        if password == admin_password:

            st.session_state[
                "admin_authenticated"
            ] = True

            st.rerun()

        else:

            st.error(
                "Incorrect password."
            )

    return False


if not check_admin_password():

    st.stop()


# =========================================================
# HEADER
# =========================================================

header_col, logout_col = st.columns(
    [8, 1],
    vertical_alignment="center",
)

with header_col:

    st.title("⚙️ Catalogue Administration")

    st.caption(
        "Add, edit, activate, deactivate and delete "
        "leather catalogue articles."
    )

with logout_col:

    if st.button(
        "Logout",
        width="stretch",
    ):

        st.session_state[
            "admin_authenticated"
        ] = False

        st.rerun()


st.divider()


# =========================================================
# IMAGE URL
# =========================================================

def get_image_url(filename):

    if not filename:

        return None

    filename = str(
        filename
    ).strip()

    if not filename:

        return None

    return (
        f"{st.secrets['SUPABASE_URL']}"
        f"/storage/v1/object/public/"
        f"{BUCKET_NAME}/"
        f"{quote(filename)}"
    )


# =========================================================
# LOAD IMAGE
# =========================================================

@st.cache_data(
    ttl=600,
    show_spinner=False,
)
def load_image(image_url):

    if not image_url:

        return None

    try:

        with urlopen(
            image_url,
            timeout=20,
        ) as response:

            image_bytes = response.read()

        return Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

    except Exception:

        return None


# =========================================================
# LOAD PRODUCTS
# =========================================================

@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def load_all_products():

    response = (
        supabase
        .table(TABLE_NAME)
        .select(
            """
            leather_id,
            article_name,
            color,
            thickness,
            tannage,
            animal,
            origin,
            main_photo,
            closeup_photo,
            is_active
            """
        )
        .order(
            "leather_id"
        )
        .execute()
    )

    return response.data or []


# =========================================================
# DUPLICATE VALIDATION
# =========================================================

def check_duplicate_product(leather_id, article_name, exclude_leather_id=None):
    """Case-insensitive duplicate check for Leather ID and Article Name."""
    lid = leather_id.strip().casefold()
    name = article_name.strip().casefold()
    for product in load_all_products():
        existing_id = str(product.get("leather_id") or "").strip()
        existing_name = str(product.get("article_name") or "").strip()
        if exclude_leather_id and existing_id.casefold() == exclude_leather_id.strip().casefold():
            continue
        if existing_id.casefold() == lid:
            return False, f"Leather ID '{leather_id}' already exists."
        if existing_name.casefold() == name:
            return False, f"Article Name '{article_name}' already exists."
    return True, ""


# =========================================================
# STORAGE HELPERS
# =========================================================

def upload_image(
    uploaded_file,
    leather_id,
    photo_type,
):

    if uploaded_file is None:

        return None

    original_name = (
        uploaded_file.name
        or "image.jpg"
    )

    extension = (
        original_name
        .rsplit(".", 1)[-1]
        .lower()
    )

    if extension not in [
        "jpg",
        "jpeg",
        "png",
        "webp",
    ]:

        extension = "jpg"

    unique_id = (
        uuid.uuid4()
        .hex[:8]
    )

    filename = (
        f"{leather_id}_"
        f"{photo_type}_"
        f"{unique_id}."
        f"{extension}"
    )

    file_bytes = uploaded_file.getvalue()

    content_type = (
        uploaded_file.type
        or "image/jpeg"
    )

    try:

        supabase.storage.from_(
            BUCKET_NAME
        ).upload(
            filename,
            file_bytes,
            {
                "content-type": content_type,
                "upsert": False,
            },
        )

        return filename

    except Exception as e:

        st.error(
            f"Unable to upload {photo_type} photo."
        )

        st.exception(e)

        return None


def delete_storage_file(filename):

    if not filename:

        return

    try:

        supabase.storage.from_(
            BUCKET_NAME
        ).remove(
            [filename]
        )

    except Exception as e:

        st.warning(
            f"Could not delete storage file: "
            f"{filename}"
        )

        st.caption(
            str(e)
        )


# =========================================================
# UPDATE DATABASE
# =========================================================

def update_product(
    leather_id,
    article_name,
    color,
    thickness,
    tannage,
    animal,
    origin,
    main_photo,
    closeup_photo,
    is_active,
):

    response = (
        supabase
        .table(TABLE_NAME)
        .update(
            {
                "article_name": article_name,
                "color": color,
                "thickness": thickness,
                "tannage": tannage,
                "animal": animal,
                "origin": origin,
                "main_photo": main_photo,
                "closeup_photo": closeup_photo,
                "is_active": is_active,
            }
        )
        .eq(
            "leather_id",
            leather_id,
        )
        .execute()
    )

    return response


# =========================================================
# CREATE PRODUCT
# =========================================================

def create_product(
    leather_id,
    article_name,
    color,
    thickness,
    tannage,
    animal,
    origin,
    main_photo,
    closeup_photo,
    is_active,
):

    response = (
        supabase
        .table(TABLE_NAME)
        .insert(
            {
                "leather_id": leather_id,
                "article_name": article_name,
                "color": color,
                "thickness": thickness,
                "tannage": tannage,
                "animal": animal,
                "origin": origin,
                "main_photo": main_photo,
                "closeup_photo": closeup_photo,
                "is_active": is_active,
            }
        )
        .execute()
    )

    return response


# =========================================================
# DELETE PRODUCT
# =========================================================

def delete_product(product):

    leather_id = product.get(
        "leather_id"
    )

    main_photo = product.get(
        "main_photo"
    )

    closeup_photo = product.get(
        "closeup_photo"
    )

    try:

        (
            supabase
            .table(TABLE_NAME)
            .delete()
            .eq(
                "leather_id",
                leather_id,
            )
            .execute()
        )

        if main_photo:

            delete_storage_file(
                main_photo
            )

        if (
            closeup_photo
            and closeup_photo != main_photo
        ):

            delete_storage_file(
                closeup_photo
            )

        return True

    except Exception as e:

        st.error(
            "Unable to delete leather article."
        )

        st.exception(e)

        return False


# =========================================================
# REFRESH
# =========================================================

refresh_col, status_col = st.columns(
    [1, 5],
    vertical_alignment="center",
)

with refresh_col:

    if st.button(
        "↻ Refresh",
        width="stretch",
    ):

        st.cache_data.clear()

        st.rerun()

with status_col:

    try:

        products = load_all_products()

        st.success(
            f"{len(products)} leather articles found."
        )

    except Exception as e:

        st.error(
            "Unable to load products."
        )

        st.exception(e)

        st.stop()


st.divider()


# =========================================================
# TABS
# =========================================================

tab_add, tab_manage = st.tabs(
    [
        "➕ Add Leather",
        "📋 Manage Catalogue",
    ]
)


# =========================================================
# ADD LEATHER
# =========================================================

with tab_add:

    st.subheader(
        "Add New Leather Article"
    )

    st.caption(
        "Create a new product and optionally upload "
        "main and close-up photos."
    )

    with st.form(
        "add_product_form",
        clear_on_submit=False,
    ):

        col1, col2 = st.columns(
            2,
            gap="large",
        )

        with col1:

            leather_id = st.text_input(
                "Leather ID *",
                placeholder="Example: BIL00021",
            )

            article_name = st.text_input(
                "Article Name *",
                placeholder="Example: Cow Lionel",
            )

            color = st.text_input(
                "Colour",
                placeholder="Example: Golden Spice",
            )

            thickness = st.text_input(
                "Thickness",
                placeholder="Example: 0.7 - 0.8",
            )

        with col2:

            animal = st.text_input(
                "Animal",
                placeholder="Example: Cow",
            )

            tannage = st.text_input(
                "Tannage",
                placeholder="Example: Semi Veg",
            )

            origin = st.text_input(
                "Origin",
                placeholder="Example: Turkey",
            )

            is_active = st.checkbox(
                "Show in customer catalogue",
                value=True,
            )

        st.divider()

        photo_col1, photo_col2 = st.columns(
            2,
            gap="large",
        )

        with photo_col1:

            main_photo_file = st.file_uploader(
                "Main Photo",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                ],
                key="add_main_photo",
            )

            if main_photo_file:

                st.image(
                    main_photo_file,
                    caption="Main Photo Preview",
                    width="stretch",
                )

        with photo_col2:

            closeup_photo_file = st.file_uploader(
                "Close-up Photo",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                ],
                key="add_closeup_photo",
            )

            if closeup_photo_file:

                st.image(
                    closeup_photo_file,
                    caption="Close-up Photo Preview",
                    width="stretch",
                )

        st.divider()

        submitted = st.form_submit_button(
            "➕ Add Leather Article",
            type="primary",
            width="stretch",
        )

    if submitted:

        leather_id = leather_id.strip()
        article_name = article_name.strip()

        if not leather_id:

            st.error(
                "Leather ID is required."
            )

        elif not article_name:

            st.error(
                "Article Name is required."
            )

        else:

            is_valid, duplicate_message = check_duplicate_product(
                leather_id=leather_id,
                article_name=article_name,
            )

            if not is_valid:
                st.error(duplicate_message)
            else:

                with st.spinner(
                    "Creating leather article..."
                ):

                    main_photo_name = None
                    closeup_photo_name = None

                    # -----------------------------------------
                    # MAIN PHOTO
                    # -----------------------------------------

                    if main_photo_file:

                        main_photo_name = (
                            upload_image(
                                main_photo_file,
                                leather_id,
                                "main",
                            )
                        )

                        if (
                            main_photo_name
                            is None
                        ):

                            st.stop()

                    # -----------------------------------------
                    # CLOSE-UP PHOTO
                    # -----------------------------------------

                    if closeup_photo_file:

                        closeup_photo_name = (
                            upload_image(
                                closeup_photo_file,
                                leather_id,
                                "closeup",
                            )
                        )

                        if (
                            closeup_photo_name
                            is None
                        ):

                            if main_photo_name:

                                delete_storage_file(
                                    main_photo_name
                                )

                            st.stop()

                    # -----------------------------------------
                    # DATABASE
                    # -----------------------------------------

                    try:

                        create_product(
                            leather_id=leather_id,
                            article_name=article_name,
                            color=color.strip(),
                            thickness=thickness.strip(),
                            tannage=tannage.strip(),
                            animal=animal.strip(),
                            origin=origin.strip(),
                            main_photo=main_photo_name,
                            closeup_photo=closeup_photo_name,
                            is_active=is_active,
                        )

                        st.cache_data.clear()

                        st.success(
                            f"{leather_id} "
                            "was added successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        # If DB insert fails,
                        # remove uploaded images.

                        if main_photo_name:

                            delete_storage_file(
                                main_photo_name
                            )

                        if closeup_photo_name:

                            delete_storage_file(
                                closeup_photo_name
                            )

                        st.error(
                            "Unable to create "
                            "the leather article."
                        )

                        st.exception(e)


# =========================================================
# MANAGE CATALOGUE
# =========================================================

with tab_manage:

    st.subheader(
        "Manage Existing Articles"
    )

    st.caption(
        "Search, edit, activate/deactivate "
        "or delete leather articles."
    )

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    search_text = st.text_input(
        "Search catalogue",
        placeholder=(
            "Search Leather ID, article, colour, "
            "animal, tannage or origin..."
        ),
        key="admin_search",
    )

    search_lower = (
        search_text
        .strip()
        .lower()
    )

    filtered_products = []

    for product in products:

        searchable_text = " ".join(
            [
                str(
                    product.get(
                        "leather_id"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "article_name"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "color"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "thickness"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "tannage"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "animal"
                    )
                    or ""
                ),

                str(
                    product.get(
                        "origin"
                    )
                    or ""
                ),
            ]
        ).lower()

        if (
            search_lower
            and search_lower
            not in searchable_text
        ):

            continue

        filtered_products.append(
            product
        )

    st.caption(
        f"Showing {len(filtered_products)} "
        f"of {len(products)} articles"
    )

    st.divider()


    # =====================================================
    # PRODUCT LIST
    # =====================================================

    for product in filtered_products:

        leather_id = str(
            product.get(
                "leather_id"
            )
            or "-"
        )

        article_name = str(
            product.get(
                "article_name"
            )
            or "-"
        )

        main_photo = product.get(
            "main_photo"
        )

        closeup_photo = product.get(
            "closeup_photo"
        )

        is_active = bool(
            product.get(
                "is_active"
            )
        )

        # -------------------------------------------------
        # PRODUCT EXPANDER
        # -------------------------------------------------

        with st.expander(
            f"{leather_id}  |  {article_name}",
            expanded=False,
        ):

            # =============================================
            # TOP INFORMATION
            # =============================================

            info_col, status_col = st.columns(
                [5, 1],
                vertical_alignment="center",
            )

            with info_col:

                st.markdown(
                    f"### {article_name}"
                )

                st.caption(
                    f"Leather ID: {leather_id}"
                )

            with status_col:

                if is_active:

                    st.success(
                        "ACTIVE"
                    )

                else:

                    st.warning(
                        "INACTIVE"
                    )


            st.divider()


            # =============================================
            # CURRENT PHOTOS
            # =============================================

            photo_col1, photo_col2 = st.columns(
                2,
                gap="large",
            )

            with photo_col1:

                st.markdown(
                    "**Main Photo**"
                )

                if main_photo:

                    main_url = get_image_url(
                        main_photo
                    )

                    main_image = load_image(
                        main_url
                    )

                    if main_image:

                        st.image(
                            main_image,
                            width="stretch",
                        )

                    else:

                        st.warning(
                            "Main photo could not "
                            "be loaded."
                        )

                    st.caption(
                        main_photo
                    )

                else:

                    st.info(
                        "No main photo."
                    )

            with photo_col2:

                st.markdown(
                    "**Close-up Photo**"
                )

                if closeup_photo:

                    closeup_url = get_image_url(
                        closeup_photo
                    )

                    closeup_image = load_image(
                        closeup_url
                    )

                    if closeup_image:

                        st.image(
                            closeup_image,
                            width="stretch",
                        )

                    else:

                        st.warning(
                            "Close-up photo could "
                            "not be loaded."
                        )

                    st.caption(
                        closeup_photo
                    )

                else:

                    st.info(
                        "No close-up photo."
                    )


            st.divider()


            # =============================================
            # EDIT FORM
            # =============================================

            st.markdown(
                "### Edit Article"
            )

            edit_col1, edit_col2 = st.columns(
                2,
                gap="large",
            )

            with edit_col1:

                edit_article_name = st.text_input(
                    "Article Name",
                    value=str(
                        product.get(
                            "article_name"
                        )
                        or ""
                    ),
                    key=f"name_{leather_id}",
                )

                edit_color = st.text_input(
                    "Colour",
                    value=str(
                        product.get(
                            "color"
                        )
                        or ""
                    ),
                    key=f"color_{leather_id}",
                )

                edit_thickness = st.text_input(
                    "Thickness",
                    value=str(
                        product.get(
                            "thickness"
                        )
                        or ""
                    ),
                    key=f"thickness_{leather_id}",
                )

                edit_animal = st.text_input(
                    "Animal",
                    value=str(
                        product.get(
                            "animal"
                        )
                        or ""
                    ),
                    key=f"animal_{leather_id}",
                )

            with edit_col2:

                edit_tannage = st.text_input(
                    "Tannage",
                    value=str(
                        product.get(
                            "tannage"
                        )
                        or ""
                    ),
                    key=f"tannage_{leather_id}",
                )

                edit_origin = st.text_input(
                    "Origin",
                    value=str(
                        product.get(
                            "origin"
                        )
                        or ""
                    ),
                    key=f"origin_{leather_id}",
                )

                edit_active = st.checkbox(
                    "Show in customer catalogue",
                    value=is_active,
                    key=f"active_{leather_id}",
                )


            st.markdown(
                "### Replace Photos"
            )

            new_photo_col1, new_photo_col2 = (
                st.columns(
                    2,
                    gap="large",
                )
            )

            with new_photo_col1:

                new_main_photo = st.file_uploader(
                    "Replace Main Photo",
                    type=[
                        "jpg",
                        "jpeg",
                        "png",
                        "webp",
                    ],
                    key=f"new_main_{leather_id}",
                )

                if new_main_photo:

                    st.image(
                        new_main_photo,
                        caption="New Main Photo",
                        width="stretch",
                    )

            with new_photo_col2:

                new_closeup_photo = st.file_uploader(
                    "Replace Close-up Photo",
                    type=[
                        "jpg",
                        "jpeg",
                        "png",
                        "webp",
                    ],
                    key=f"new_closeup_{leather_id}",
                )

                if new_closeup_photo:

                    st.image(
                        new_closeup_photo,
                        caption="New Close-up Photo",
                        width="stretch",
                    )


            # =============================================
            # ACTION BUTTONS
            # =============================================

            st.divider()

            action_col1, action_col2, action_col3 = (
                st.columns(
                    [2, 2, 2],
                    gap="medium",
                )
            )


            # ---------------------------------------------
            # SAVE CHANGES
            # ---------------------------------------------

            with action_col1:

                save_clicked = st.button(
                    "💾 Save Changes",
                    key=f"save_{leather_id}",
                    type="primary",
                    width="stretch",
                )


            # ---------------------------------------------
            # ACTIVATE / DEACTIVATE
            # ---------------------------------------------

            with action_col2:

                if is_active:

                    status_clicked = st.button(
                        "⏸ Deactivate",
                        key=f"status_{leather_id}",
                        width="stretch",
                    )

                else:

                    status_clicked = st.button(
                        "▶ Activate",
                        key=f"status_{leather_id}",
                        width="stretch",
                    )


            # ---------------------------------------------
            # DELETE
            # ---------------------------------------------

            with action_col3:

                delete_clicked = st.button(
                    "🗑️ Delete",
                    key=f"delete_{leather_id}",
                    width="stretch",
                )


            # =============================================
            # SAVE
            # =============================================

            if save_clicked:

                if not edit_article_name.strip():
                    st.error("Article Name cannot be empty.")

                else:
                    is_valid, duplicate_message = check_duplicate_product(
                        leather_id=leather_id,
                        article_name=edit_article_name,
                        exclude_leather_id=leather_id,
                    )

                    if not is_valid:
                        st.error(duplicate_message)
                    else:
                        new_main_photo_name = main_photo

                        new_closeup_photo_name = (
                            closeup_photo
                        )

                        upload_success = True

                        # -------------------------------------
                        # NEW MAIN PHOTO
                        # -------------------------------------

                        if new_main_photo:

                            uploaded_main_name = (
                                upload_image(
                                    new_main_photo,
                                    leather_id,
                                    "main",
                                )
                            )

                            if uploaded_main_name:

                                new_main_photo_name = (
                                    uploaded_main_name
                                )

                            else:

                                upload_success = False


                        # -------------------------------------
                        # NEW CLOSE-UP PHOTO
                        # -------------------------------------

                        if (
                            upload_success
                            and new_closeup_photo
                        ):

                            uploaded_closeup_name = (
                                upload_image(
                                    new_closeup_photo,
                                    leather_id,
                                    "closeup",
                                )
                            )

                            if uploaded_closeup_name:

                                new_closeup_photo_name = (
                                    uploaded_closeup_name
                                )

                            else:

                                upload_success = False


                        if upload_success:

                            try:

                                update_product(
                                    leather_id=leather_id,
                                    article_name=(
                                        edit_article_name
                                        .strip()
                                    ),
                                    color=(
                                        edit_color
                                        .strip()
                                    ),
                                    thickness=(
                                        edit_thickness
                                        .strip()
                                    ),
                                    tannage=(
                                        edit_tannage
                                        .strip()
                                    ),
                                    animal=(
                                        edit_animal
                                        .strip()
                                    ),
                                    origin=(
                                        edit_origin
                                        .strip()
                                    ),
                                    main_photo=(
                                        new_main_photo_name
                                    ),
                                    closeup_photo=(
                                        new_closeup_photo_name
                                    ),
                                    is_active=(
                                        edit_active
                                    ),
                                )

                                # ---------------------------------
                                # DELETE OLD MAIN PHOTO
                                # ---------------------------------

                                if (
                                    new_main_photo
                                    and main_photo
                                    and main_photo
                                    != new_main_photo_name
                                ):

                                    delete_storage_file(
                                        main_photo
                                    )


                                # ---------------------------------
                                # DELETE OLD CLOSE-UP PHOTO
                                # ---------------------------------

                                if (
                                    new_closeup_photo
                                    and closeup_photo
                                    and closeup_photo
                                    != new_closeup_photo_name
                                ):

                                    delete_storage_file(
                                        closeup_photo
                                    )


                                st.cache_data.clear()

                                st.success(
                                    f"{leather_id} "
                                    "updated successfully."
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    "Unable to update "
                                    "the article."
                                )

                                st.exception(e)


            # =============================================
            # ACTIVATE / DEACTIVATE
            # =============================================

            if status_clicked:

                try:

                    (
                        supabase
                        .table(TABLE_NAME)
                        .update(
                            {
                                "is_active":
                                    not is_active
                            }
                        )
                        .eq(
                            "leather_id",
                            leather_id,
                        )
                        .execute()
                    )

                    st.cache_data.clear()

                    if is_active:

                        st.success(
                            f"{leather_id} "
                            "has been deactivated."
                        )

                    else:

                        st.success(
                            f"{leather_id} "
                            "has been activated."
                        )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Unable to change "
                        "article status."
                    )

                    st.exception(e)

            
            # =============================================
            # DELETE
            # =============================================
            
            if delete_clicked:
            
                st.session_state["delete_confirm_id"] = leather_id
            
            
            # Show confirmation if this product is waiting
            # for deletion confirmation.
            
            if (
                st.session_state.get("delete_confirm_id")
                == leather_id
            ):
            
                st.warning(
                    f"Are you sure you want to permanently delete "
                    f"**{leather_id} | {article_name}**?"
                )
            
                confirm_col1, confirm_col2 = st.columns(
                    2,
                    gap="medium",
                )
            
                with confirm_col1:
            
                    confirm_delete = st.button(
                        "🗑️ Yes, permanently delete",
                        key=f"confirm_delete_{leather_id}",
                        type="primary",
                        width="stretch",
                    )
            
                with confirm_col2:
            
                    cancel_delete = st.button(
                        "Cancel",
                        key=f"cancel_delete_{leather_id}",
                        width="stretch",
                    )
            
                if cancel_delete:
            
                    st.session_state.pop(
                        "delete_confirm_id",
                        None,
                    )
            
                    st.rerun()
            
                if confirm_delete:
            
                    with st.spinner(
                        f"Deleting {leather_id}..."
                    ):
            
                        try:
            
                            # -----------------------------------------
                            # DELETE DATABASE RECORD FIRST
                            # -----------------------------------------
            
                            delete_response = (
                                supabase
                                .table(TABLE_NAME)
                                .delete()
                                .eq(
                                    "leather_id",
                                    leather_id,
                                )
                                .execute()
                            )
            
                            # -----------------------------------------
                            # DELETE MAIN PHOTO
                            # -----------------------------------------
            
                            if main_photo:
            
                                delete_storage_file(
                                    main_photo
                                )
            
                            # -----------------------------------------
                            # DELETE CLOSE-UP PHOTO
                            # -----------------------------------------
            
                            if (
                                closeup_photo
                                and closeup_photo != main_photo
                            ):
            
                                delete_storage_file(
                                    closeup_photo
                                )
            
                            # -----------------------------------------
                            # CLEAR DELETE STATE
                            # -----------------------------------------
            
                            st.session_state.pop(
                                "delete_confirm_id",
                                None,
                            )
            
                            # -----------------------------------------
                            # CLEAR CACHE
                            # -----------------------------------------
            
                            st.cache_data.clear()
            
                            st.success(
                                f"{leather_id} was permanently deleted."
                            )
            
                            st.rerun()
            
                        except Exception as e:
            
                            st.error(
                                f"Unable to delete {leather_id}."
                            )
            
                            st.exception(e)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Leather Catalogue Administration • "
    "Bhartiya Fashions"
)
