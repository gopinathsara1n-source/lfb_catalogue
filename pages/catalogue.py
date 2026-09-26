import streamlit as st
from supabase import create_client
from urllib.parse import quote
from io import BytesIO
from urllib.request import urlopen
from PIL import Image
import uuid
import hmac
import html
import base64
import json


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Leather Catalogue",
    page_icon="🧥",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONSTANTS
# ============================================================

TABLE_NAME = "leather_products"
BUCKET_NAME = "leather-images"

IMAGE_TYPES = [
    "jpg",
    "jpeg",
    "png",
    "webp",
]


# ============================================================
# SESSION STATE
# ============================================================

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "admin_login_error" not in st.session_state:
    st.session_state.admin_login_error = False


# ============================================================
# SUPABASE - CUSTOMER CONNECTION
# ============================================================

@st.cache_resource
def get_customer_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


# ============================================================
# SUPABASE - ADMIN CONNECTION
# ============================================================

@st.cache_resource
def get_admin_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )


# ============================================================
# CUSTOMER SUPABASE
# ============================================================

try:

    customer_supabase = get_customer_supabase()

except Exception as e:

    st.error("Unable to connect to the catalogue database.")

    st.info(
        "Please check SUPABASE_URL and SUPABASE_KEY "
        "in Streamlit secrets."
    )

    st.exception(e)

    st.stop()


# ============================================================
# IMAGE URL
# ============================================================

def get_image_url(filename):

    if not filename:
        return None

    filename = str(filename).strip()

    if not filename:
        return None

    return (
        f"{st.secrets['SUPABASE_URL']}"
        f"/storage/v1/object/public/"
        f"{BUCKET_NAME}/"
        f"{quote(filename)}"
    )


# ============================================================
# LOAD IMAGE
# ============================================================

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


# ============================================================
# LOAD ACTIVE PRODUCTS
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def load_products():

    response = (
        customer_supabase
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
        .eq(
            "is_active",
            True,
        )
        .order(
            "leather_id"
        )
        .execute()
    )

    return response.data or []


# ============================================================
# ADMIN PASSWORD
# ============================================================

def check_admin_password():

    if st.session_state.admin_authenticated:
        return True

    st.markdown(
        """
        <div style="
            max-width:500px;
            margin:40px auto 20px auto;
            padding:30px;
            border-radius:16px;
            border:1px solid rgba(128,128,128,0.25);
        ">
            <h2 style="text-align:center;">
                🔐 Catalogue Administration
            </h2>
            <p style="
                text-align:center;
                opacity:0.7;
            ">
                Restricted access
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    password = st.text_input(
        "Admin Password",
        type="password",
        placeholder="Enter admin password",
        key="admin_password_input",
    )

    if st.button(
        "Login",
        type="primary",
        width="stretch",
        key="admin_login_button",
    ):

        configured_password = st.secrets.get(
            "ADMIN_PASSWORD"
        )

        if not configured_password:

            st.error(
                "ADMIN_PASSWORD is not configured "
                "in Streamlit secrets."
            )

            return False

        if hmac.compare_digest(
            password,
            str(configured_password),
        ):

            st.session_state.admin_authenticated = True
            st.session_state.admin_login_error = False

            st.rerun()

        else:

            st.session_state.admin_login_error = True
            st.error("Incorrect admin password.")

    return False


# ============================================================
# ADMIN CONNECTION
# ============================================================

def get_admin_client():

    try:

        return get_admin_supabase()

    except Exception as e:

        st.error(
            "Admin database connection could not be established."
        )

        st.exception(e)

        return None


# ============================================================
# LOAD ALL PRODUCTS - ADMIN
# ============================================================

@st.cache_data(
    ttl=30,
    show_spinner=False,
)
def load_all_products():

    admin_supabase = get_admin_supabase()

    response = (
        admin_supabase
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


# ============================================================
# DUPLICATE CHECK
# ============================================================

def check_duplicate_product(
    leather_id,
    article_name,
    exclude_leather_id=None,
):

    leather_id = str(
        leather_id or ""
    ).strip().casefold()

    article_name = str(
        article_name or ""
    ).strip().casefold()

    exclude_id = None

    if exclude_leather_id:
        exclude_id = str(
            exclude_leather_id
        ).strip().casefold()

    for product in load_all_products():

        existing_id = str(
            product.get("leather_id") or ""
        ).strip()

        existing_name = str(
            product.get("article_name") or ""
        ).strip()

        if (
            exclude_id
            and existing_id.casefold() == exclude_id
        ):
            continue

        if existing_id.casefold() == leather_id:

            return (
                False,
                f"Leather ID '{leather_id}' already exists.",
            )

        if existing_name.casefold() == article_name:

            return (
                False,
                f"Article Name '{article_name}' already exists.",
            )

    return True, ""


# ============================================================
# STORAGE - UPLOAD
# ============================================================

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

    if "." in original_name:

        extension = (
            original_name
            .rsplit(".", 1)[-1]
            .lower()
        )

    else:

        extension = "jpg"

    if extension not in IMAGE_TYPES:
        extension = "jpg"

    unique_id = uuid.uuid4().hex[:10]

    safe_leather_id = (
        str(leather_id)
        .strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    filename = (
        f"{safe_leather_id}_"
        f"{photo_type}_"
        f"{unique_id}."
        f"{extension}"
    )

    try:

        admin_supabase = get_admin_supabase()

        admin_supabase.storage.from_(
            BUCKET_NAME
        ).upload(
            filename,
            uploaded_file.getvalue(),
            {
                "content-type": (
                    uploaded_file.type
                    or "image/jpeg"
                ),
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


# ============================================================
# STORAGE - DELETE
# ============================================================

def delete_storage_file(filename):

    if not filename:
        return True

    try:

        admin_supabase = get_admin_supabase()

        admin_supabase.storage.from_(
            BUCKET_NAME
        ).remove(
            [filename]
        )

        return True

    except Exception as e:

        st.warning(
            f"Could not delete storage file: {filename}"
        )

        st.caption(str(e))

        return False


# ============================================================
# CREATE PRODUCT
# ============================================================

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

    admin_supabase = get_admin_supabase()

    return (
        admin_supabase
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


# ============================================================
# UPDATE PRODUCT
# ============================================================

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

    admin_supabase = get_admin_supabase()

    return (
        admin_supabase
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


# ============================================================
# DELETE PRODUCT
# ============================================================

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

        admin_supabase = get_admin_supabase()

        # Delete database record first
        (
            admin_supabase
            .table(TABLE_NAME)
            .delete()
            .eq(
                "leather_id",
                leather_id,
            )
            .execute()
        )

        # Then delete storage files
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


# ============================================================
# CUSTOMER IMAGE SLIDER
# ============================================================

def render_image_slider(
    main_url,
    closeup_url,
    height=350,
):

    images = [
        url
        for url in [
            main_url,
            closeup_url,
        ]
        if url
    ]

    if not images:
        return

    encoded_images = []

    for image_url in images:

        encoded_images.append(
            json.dumps(image_url)
        )

    images_json = "[" + ",".join(
        encoded_images
    ) + "]"

    slider_html = f"""
    <div style="
        width:100%;
        height:{height}px;
        overflow:hidden;
        border-radius:12px;
        background:#f5f5f5;
        position:relative;
    ">

        <img
            id="catalogue-slide-image"
            src={json.dumps(images[0])}
            style="
                width:100%;
                height:100%;
                object-fit:cover;
                display:block;
            "
        />

    </div>

    <script>

        const catalogueImages = {images_json};

        let catalogueIndex = 0;

        const catalogueImage =
            document.getElementById(
                "catalogue-slide-image"
            );

        if (catalogueImages.length > 1) {{

            setInterval(function() {{

                catalogueIndex =
                    (catalogueIndex + 1)
                    % catalogueImages.length;

                catalogueImage.src =
                    catalogueImages[catalogueIndex];

            }}, 5000);

        }}

    </script>
    """

    st.components.v1.html(
        slider_html,
        height=height + 10,
    )


# ============================================================
# DETAIL IMAGE VIEWER
# ============================================================

def render_detail_image(
    image_url,
    key,
):

    if not image_url:
        st.info("No image available.")
        return

    image = load_image(image_url)

    if image is None:

        st.image(
            image_url,
            width="stretch",
        )

        return

    buffered = BytesIO()

    image.save(
        buffered,
        format="JPEG",
        quality=90,
    )

    image_base64 = base64.b64encode(
        buffered.getvalue()
    ).decode()

    viewer_html = f"""
    <div style="
        width:100%;
        height:550px;
        overflow:hidden;
        position:relative;
        border-radius:12px;
        background:#f5f5f5;
        cursor:grab;
    ">

        <img
            id="zoom-image-{key}"
            src="data:image/jpeg;base64,{image_base64}"
            style="
                max-width:none;
                width:100%;
                height:100%;
                object-fit:contain;
                transform-origin:center center;
                user-select:none;
                transition:transform 0.08s;
            "
        />

    </div>

    <script>

        const image =
            document.getElementById(
                "zoom-image-{key}"
            );

        let scale = 1;
        let posX = 0;
        let posY = 0;

        let dragging = false;
        let startX = 0;
        let startY = 0;

        function updateImage() {{

            image.style.transform =
                `translate(${{posX}}px, ${{posY}}px)
                 scale(${{scale}})`;

        }}

        image.parentElement.addEventListener(
            "wheel",
            function(event) {{

                event.preventDefault();

                if (event.deltaY < 0) {{
                    scale += 0.15;
                }} else {{
                    scale -= 0.15;
                }}

                scale = Math.max(
                    1,
                    Math.min(5, scale)
                );

                updateImage();

            }},
            {{ passive:false }}
        );

        image.parentElement.addEventListener(
            "mousedown",
            function(event) {{

                dragging = true;

                startX = event.clientX - posX;
                startY = event.clientY - posY;

                image.parentElement.style.cursor =
                    "grabbing";

            }}
        );

        window.addEventListener(
            "mouseup",
            function() {{

                dragging = false;

                image.parentElement.style.cursor =
                    "grab";

            }}
        );

        window.addEventListener(
            "mousemove",
            function(event) {{

                if (!dragging) return;

                posX =
                    event.clientX - startX;

                posY =
                    event.clientY - startY;

                updateImage();

            }}
        );

    </script>
    """

    st.components.v1.html(
        viewer_html,
        height=560,
    )


# ============================================================
# PRODUCT DETAIL
# ============================================================

@st.dialog("Leather Details", width="large")
def show_product_details(product):

    leather_id = product.get(
        "leather_id"
    )

    article_name = product.get(
        "article_name"
    )

    main_photo = product.get(
        "main_photo"
    )

    closeup_photo = product.get(
        "closeup_photo"
    )

    main_url = get_image_url(
        main_photo
    )

    closeup_url = get_image_url(
        closeup_photo
    )

    st.subheader(
        article_name or "-"
    )

    st.caption(
        f"Leather ID: {leather_id or '-'}"
    )

    image_options = []

    if main_url:
        image_options.append(
            ("Main Photo", main_url)
        )

    if closeup_url:
        image_options.append(
            ("Close-up Photo", closeup_url)
        )

    if image_options:

        selected_image = st.selectbox(
            "View Image",
            options=[
                item[0]
                for item in image_options
            ],
            key=f"detail_image_{leather_id}",
        )

        selected_url = dict(
            image_options
        )[selected_image]

        render_detail_image(
            selected_url,
            key=str(leather_id).replace(
                " ",
                "_",
            ),
        )

    else:

        st.info(
            "No photos available for this article."
        )

    st.divider()

    info_col1, info_col2 = st.columns(2)

    with info_col1:

        st.markdown(
            f"**Colour**  \n"
            f"{product.get('color') or '-'}"
        )

        st.markdown(
            f"**Thickness**  \n"
            f"{product.get('thickness') or '-'}"
        )

        st.markdown(
            f"**Animal**  \n"
            f"{product.get('animal') or '-'}"
        )

    with info_col2:

        st.markdown(
            f"**Tannage**  \n"
            f"{product.get('tannage') or '-'}"
        )

        st.markdown(
            f"**Origin**  \n"
            f"{product.get('origin') or '-'}"
        )

        st.markdown(
            f"**Article Name**  \n"
            f"{article_name or '-'}"
        )


# ============================================================
# ADMIN PANEL
# ============================================================

def render_admin_panel():

    st.markdown(
        """
        <div style="
            padding:18px 22px;
            border-radius:14px;
            background:rgba(128,128,128,0.08);
            border:1px solid rgba(128,128,128,0.20);
            margin-bottom:20px;
        ">
            <h2 style="margin:0;">
                ⚙️ Catalogue Administration
            </h2>
            <p style="margin:5px 0 0 0; opacity:0.7;">
                Restricted catalogue management
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    header_col, logout_col = st.columns(
        [8, 1],
        vertical_alignment="center",
    )

    with header_col:

        st.caption(
            "Add, edit, activate, deactivate and "
            "delete leather catalogue articles."
        )

    with logout_col:

        if st.button(
            "Logout",
            width="stretch",
            key="admin_logout",
        ):

            st.session_state.admin_authenticated = False

            st.rerun()

    st.divider()

    # --------------------------------------------------------
    # LOAD PRODUCTS
    # --------------------------------------------------------

    try:

        products = load_all_products()

    except Exception as e:

        st.error(
            "Unable to load catalogue."
        )

        st.exception(e)

        return

    refresh_col, status_col = st.columns(
        [1, 5],
        vertical_alignment="center",
    )

    with refresh_col:

        if st.button(
            "↻ Refresh",
            width="stretch",
            key="admin_refresh",
        ):

            st.cache_data.clear()

            st.rerun()

    with status_col:

        active_count = sum(
            bool(
                p.get("is_active")
            )
            for p in products
        )

        inactive_count = (
            len(products)
            - active_count
        )

        st.info(
            f"Total: {len(products)}  |  "
            f"Active: {active_count}  |  "
            f"Inactive: {inactive_count}"
        )

    st.divider()

    tab_add, tab_manage = st.tabs(
        [
            "➕ Add Leather",
            "📋 Manage Catalogue",
        ]
    )

    # ========================================================
    # ADD LEATHER
    # ========================================================

    with tab_add:

        st.subheader(
            "Add New Leather Article"
        )

        with st.form(
            "admin_add_product_form",
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
                    placeholder="Example: 0.7 - 0.8 mm",
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
                    type=IMAGE_TYPES,
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
                    type=IMAGE_TYPES,
                    key="add_closeup_photo",
                )

                if closeup_photo_file:

                    st.image(
                        closeup_photo_file,
                        caption="Close-up Photo Preview",
                        width="stretch",
                    )

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

                valid, message = (
                    check_duplicate_product(
                        leather_id,
                        article_name,
                    )
                )

                if not valid:

                    st.error(message)

                else:

                    main_photo_name = None
                    closeup_photo_name = None

                    with st.spinner(
                        "Creating leather article..."
                    ):

                        # Upload main image
                        if main_photo_file:

                            main_photo_name = upload_image(
                                main_photo_file,
                                leather_id,
                                "main",
                            )

                            if not main_photo_name:

                                st.stop()

                        # Upload close-up
                        if closeup_photo_file:

                            closeup_photo_name = upload_image(
                                closeup_photo_file,
                                leather_id,
                                "closeup",
                            )

                            if not closeup_photo_name:

                                if main_photo_name:
                                    delete_storage_file(
                                        main_photo_name
                                    )

                                st.stop()

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

    # ========================================================
    # MANAGE CATALOGUE
    # ========================================================

    with tab_manage:

        st.subheader(
            "Manage Existing Articles"
        )

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
            .casefold()
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
            ).casefold()

            if (
                search_lower
                and search_lower not in searchable_text
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

        # ----------------------------------------------------
        # PRODUCTS
        # ----------------------------------------------------

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

            is_active = bool(
                product.get(
                    "is_active"
                )
            )

            status_text = (
                "🟢 Active"
                if is_active
                else "🔴 Inactive"
            )

            with st.expander(
                f"{leather_id}  |  "
                f"{article_name}  |  "
                f"{status_text}",
                expanded=False,
            ):

                # ============================================
                # CURRENT INFORMATION
                # ============================================

                current_col1, current_col2 = st.columns(
                    [2, 3],
                    gap="large",
                )

                with current_col1:

                    main_url = get_image_url(
                        product.get(
                            "main_photo"
                        )
                    )

                    closeup_url = get_image_url(
                        product.get(
                            "closeup_photo"
                        )
                    )

                    if main_url:

                        st.image(
                            main_url,
                            caption="Main Photo",
                            width="stretch",
                        )

                    if closeup_url:

                        st.image(
                            closeup_url,
                            caption="Close-up Photo",
                            width="stretch",
                        )

                with current_col2:

                    st.markdown(
                        f"**Leather ID:** "
                        f"{leather_id}"
                    )

                    st.markdown(
                        f"**Article Name:** "
                        f"{article_name}"
                    )

                    st.markdown(
                        f"**Colour:** "
                        f"{product.get('color') or '-'}"
                    )

                    st.markdown(
                        f"**Thickness:** "
                        f"{product.get('thickness') or '-'}"
                    )

                    st.markdown(
                        f"**Animal:** "
                        f"{product.get('animal') or '-'}"
                    )

                    st.markdown(
                        f"**Tannage:** "
                        f"{product.get('tannage') or '-'}"
                    )

                    st.markdown(
                        f"**Origin:** "
                        f"{product.get('origin') or '-'}"
                    )

                st.divider()

                # ============================================
                # EDIT
                # ============================================

                st.markdown(
                    "### ✏️ Edit Article"
                )

                edit_col1, edit_col2 = st.columns(
                    2,
                    gap="large",
                )

                with edit_col1:

                    new_article_name = st.text_input(
                        "Article Name",
                        value=(
                            product.get(
                                "article_name"
                            )
                            or ""
                        ),
                        key=f"edit_name_{leather_id}",
                    )

                    new_color = st.text_input(
                        "Colour",
                        value=(
                            product.get(
                                "color"
                            )
                            or ""
                        ),
                        key=f"edit_color_{leather_id}",
                    )

                    new_thickness = st.text_input(
                        "Thickness",
                        value=(
                            product.get(
                                "thickness"
                            )
                            or ""
                        ),
                        key=f"edit_thickness_{leather_id}",
                    )

                    new_animal = st.text_input(
                        "Animal",
                        value=(
                            product.get(
                                "animal"
                            )
                            or ""
                        ),
                        key=f"edit_animal_{leather_id}",
                    )

                with edit_col2:

                    new_tannage = st.text_input(
                        "Tannage",
                        value=(
                            product.get(
                                "tannage"
                            )
                            or ""
                        ),
                        key=f"edit_tannage_{leather_id}",
                    )

                    new_origin = st.text_input(
                        "Origin",
                        value=(
                            product.get(
                                "origin"
                            )
                            or ""
                        ),
                        key=f"edit_origin_{leather_id}",
                    )

                    new_active = st.checkbox(
                        "Show in customer catalogue",
                        value=is_active,
                        key=f"edit_active_{leather_id}",
                    )

                if st.button(
                    "💾 Save Changes",
                    type="primary",
                    key=f"save_{leather_id}",
                ):

                    new_article_name = (
                        new_article_name
                        .strip()
                    )

                    if not new_article_name:

                        st.error(
                            "Article Name is required."
                        )

                    else:

                        valid, message = (
                            check_duplicate_product(
                                leather_id=leather_id,
                                article_name=new_article_name,
                                exclude_leather_id=leather_id,
                            )
                        )

                        if not valid:

                            st.error(message)

                        else:

                            try:

                                update_product(
                                    leather_id=leather_id,
                                    article_name=new_article_name,
                                    color=new_color.strip(),
                                    thickness=new_thickness.strip(),
                                    tannage=new_tannage.strip(),
                                    animal=new_animal.strip(),
                                    origin=new_origin.strip(),
                                    main_photo=product.get(
                                        "main_photo"
                                    ),
                                    closeup_photo=product.get(
                                        "closeup_photo"
                                    ),
                                    is_active=new_active,
                                )

                                st.cache_data.clear()

                                st.success(
                                    "Article updated successfully."
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    "Unable to update article."
                                )

                                st.exception(e)

                st.divider()

                # ============================================
                # REPLACE PHOTOS
                # ============================================

                st.markdown(
                    "### 📷 Replace Photos"
                )

                photo_col1, photo_col2 = st.columns(
                    2,
                    gap="large",
                )

                with photo_col1:

                    new_main_photo = st.file_uploader(
                        "Replace Main Photo",
                        type=IMAGE_TYPES,
                        key=f"new_main_{leather_id}",
                    )

                with photo_col2:

                    new_closeup_photo = st.file_uploader(
                        "Replace Close-up Photo",
                        type=IMAGE_TYPES,
                        key=f"new_closeup_{leather_id}",
                    )

                if st.button(
                    "📷 Update Photos",
                    key=f"update_photos_{leather_id}",
                ):

                    if (
                        not new_main_photo
                        and not new_closeup_photo
                    ):

                        st.warning(
                            "Please select at least one photo."
                        )

                    else:

                        old_main = product.get(
                            "main_photo"
                        )

                        old_closeup = product.get(
                            "closeup_photo"
                        )

                        uploaded_main = None
                        uploaded_closeup = None

                        try:

                            # --------------------------------
                            # MAIN
                            # --------------------------------

                            if new_main_photo:

                                uploaded_main = upload_image(
                                    new_main_photo,
                                    leather_id,
                                    "main",
                                )

                                if not uploaded_main:

                                    st.stop()

                            else:

                                uploaded_main = old_main

                            # --------------------------------
                            # CLOSEUP
                            # --------------------------------

                            if new_closeup_photo:

                                uploaded_closeup = upload_image(
                                    new_closeup_photo,
                                    leather_id,
                                    "closeup",
                                )

                                if not uploaded_closeup:

                                    if (
                                        new_main_photo
                                        and uploaded_main
                                        and uploaded_main != old_main
                                    ):
                                        delete_storage_file(
                                            uploaded_main
                                        )

                                    st.stop()

                            else:

                                uploaded_closeup = old_closeup

                            # --------------------------------
                            # DATABASE
                            # --------------------------------

                            update_product(
                                leather_id=leather_id,
                                article_name=(
                                    product.get(
                                        "article_name"
                                    )
                                    or ""
                                ),
                                color=(
                                    product.get(
                                        "color"
                                    )
                                    or ""
                                ),
                                thickness=(
                                    product.get(
                                        "thickness"
                                    )
                                    or ""
                                ),
                                tannage=(
                                    product.get(
                                        "tannage"
                                    )
                                    or ""
                                ),
                                animal=(
                                    product.get(
                                        "animal"
                                    )
                                    or ""
                                ),
                                origin=(
                                    product.get(
                                        "origin"
                                    )
                                    or ""
                                ),
                                main_photo=uploaded_main,
                                closeup_photo=uploaded_closeup,
                                is_active=is_active,
                            )

                            # --------------------------------
                            # DELETE OLD FILES
                            # --------------------------------

                            if (
                                new_main_photo
                                and old_main
                                and uploaded_main != old_main
                            ):

                                delete_storage_file(
                                    old_main
                                )

                            if (
                                new_closeup_photo
                                and old_closeup
                                and uploaded_closeup != old_closeup
                            ):

                                delete_storage_file(
                                    old_closeup
                                )

                            st.cache_data.clear()

                            st.success(
                                "Photos updated successfully."
                            )

                            st.rerun()

                        except Exception as e:

                            # Clean newly uploaded files
                            # if DB update fails

                            if (
                                uploaded_main
                                and uploaded_main != old_main
                            ):

                                delete_storage_file(
                                    uploaded_main
                                )

                            if (
                                uploaded_closeup
                                and uploaded_closeup != old_closeup
                            ):

                                delete_storage_file(
                                    uploaded_closeup
                                )

                            st.error(
                                "Unable to update photos."
                            )

                            st.exception(e)

                st.divider()

                # ============================================
                # ACTIVATE / DEACTIVATE
                # ============================================

                st.markdown(
                    "### 🔄 Catalogue Status"
                )

                if is_active:

                    st.success(
                        "This article is currently visible "
                        "in the customer catalogue."
                    )

                    if st.button(
                        "🔴 Deactivate Article",
                        key=f"deactivate_{leather_id}",
                    ):

                        try:

                            update_product(
                                leather_id=leather_id,
                                article_name=(
                                    product.get(
                                        "article_name"
                                    )
                                    or ""
                                ),
                                color=(
                                    product.get(
                                        "color"
                                    )
                                    or ""
                                ),
                                thickness=(
                                    product.get(
                                        "thickness"
                                    )
                                    or ""
                                ),
                                tannage=(
                                    product.get(
                                        "tannage"
                                    )
                                    or ""
                                ),
                                animal=(
                                    product.get(
                                        "animal"
                                    )
                                    or ""
                                ),
                                origin=(
                                    product.get(
                                        "origin"
                                    )
                                    or ""
                                ),
                                main_photo=product.get(
                                    "main_photo"
                                ),
                                closeup_photo=product.get(
                                    "closeup_photo"
                                ),
                                is_active=False,
                            )

                            st.cache_data.clear()

                            st.success(
                                "Article deactivated."
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Unable to deactivate article."
                            )

                            st.exception(e)

                else:

                    st.warning(
                        "This article is currently hidden "
                        "from the customer catalogue."
                    )

                    if st.button(
                        "🟢 Activate Article",
                        key=f"activate_{leather_id}",
                    ):

                        try:

                            update_product(
                                leather_id=leather_id,
                                article_name=(
                                    product.get(
                                        "article_name"
                                    )
                                    or ""
                                ),
                                color=(
                                    product.get(
                                        "color"
                                    )
                                    or ""
                                ),
                                thickness=(
                                    product.get(
                                        "thickness"
                                    )
                                    or ""
                                ),
                                tannage=(
                                    product.get(
                                        "tannage"
                                    )
                                    or ""
                                ),
                                animal=(
                                    product.get(
                                        "animal"
                                    )
                                    or ""
                                ),
                                origin=(
                                    product.get(
                                        "origin"
                                    )
                                    or ""
                                ),
                                main_photo=product.get(
                                    "main_photo"
                                ),
                                closeup_photo=product.get(
                                    "closeup_photo"
                                ),
                                is_active=True,
                            )

                            st.cache_data.clear()

                            st.success(
                                "Article activated."
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Unable to activate article."
                            )

                            st.exception(e)

                st.divider()

                # ============================================
                # DELETE
                # ============================================

                st.markdown(
                    "### 🗑️ Delete Article"
                )

                st.warning(
                    "Deletion is permanent. "
                    "The database record and associated "
                    "photos will be removed."
                )

                confirm_delete = st.checkbox(
                    "I understand that this article will be permanently deleted.",
                    key=f"confirm_delete_{leather_id}",
                )

                if st.button(
                    "🗑️ Permanently Delete",
                    type="secondary",
                    key=f"delete_{leather_id}",
                    disabled=not confirm_delete,
                ):

                    with st.spinner(
                        "Deleting article..."
                    ):

                        if delete_product(product):

                            st.cache_data.clear()

                            st.success(
                                f"{leather_id} deleted successfully."
                            )

                            st.rerun()


# ============================================================
# CUSTOMER CATALOGUE
# ============================================================

def render_catalogue():

    # ========================================================
    # HEADER
    # ========================================================

    header_col, admin_col = st.columns(
        [8, 1],
        vertical_alignment="center",
    )

    with header_col:

        st.title("Leather Catalogue")

        st.caption(
            "Explore our leather collection"
        )

    with admin_col:

        if st.button(
            "⚙️ Admin",
            width="stretch",
            key="open_admin",
        ):

            st.session_state.show_admin_login = True

    st.divider()

    # ========================================================
    # PRODUCTS
    # ========================================================

    try:

        products = load_products()

    except Exception as e:

        st.error(
            "Unable to load leather catalogue."
        )

        st.exception(e)

        return

    if not products:

        st.info(
            "No leather articles are currently available."
        )

        return

    # ========================================================
    # FILTER VALUES
    # ========================================================

    animal_values = sorted(
        {
            str(
                p.get("animal")
            ).strip()
            for p in products
            if p.get("animal")
        }
    )

    tannage_values = sorted(
        {
            str(
                p.get("tannage")
            ).strip()
            for p in products
            if p.get("tannage")
        }
    )

    color_values = sorted(
        {
            str(
                p.get("color")
            ).strip()
            for p in products
            if p.get("color")
        }
    )

    origin_values = sorted(
        {
            str(
                p.get("origin")
            ).strip()
            for p in products
            if p.get("origin")
        }
    )

    # ========================================================
    # SEARCH
    # ========================================================

    search_text = st.text_input(
        "🔎 Search",
        placeholder=(
            "Search Leather ID, article, colour, "
            "thickness, tannage, animal or origin..."
        ),
        key="catalogue_search",
    )

    # ========================================================
    # FILTERS
    # ========================================================

    filter_col1, filter_col2, filter_col3, filter_col4 = (
        st.columns(4)
    )

    with filter_col1:

        selected_animal = st.selectbox(
            "Animal",
            ["All"] + animal_values,
            key="filter_animal",
        )

    with filter_col2:

        selected_tannage = st.selectbox(
            "Tannage",
            ["All"] + tannage_values,
            key="filter_tannage",
        )

    with filter_col3:

        selected_color = st.selectbox(
            "Colour",
            ["All"] + color_values,
            key="filter_color",
        )

    with filter_col4:

        selected_origin = st.selectbox(
            "Origin",
            ["All"] + origin_values,
            key="filter_origin",
        )

    sort_option = st.selectbox(
        "Sort by",
        [
            "Leather ID",
            "Article",
            "Animal",
            "Colour",
        ],
        key="catalogue_sort",
    )

    # ========================================================
    # FILTER PRODUCTS
    # ========================================================

    search_lower = (
        search_text
        .strip()
        .casefold()
    )

    filtered_products = []

    for product in products:

        # Search
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
        ).casefold()

        if (
            search_lower
            and search_lower not in searchable_text
        ):

            continue

        # Animal
        if (
            selected_animal != "All"
            and str(
                product.get("animal")
                or ""
            ).strip()
            != selected_animal
        ):

            continue

        # Tannage
        if (
            selected_tannage != "All"
            and str(
                product.get("tannage")
                or ""
            ).strip()
            != selected_tannage
        ):

            continue

        # Colour
        if (
            selected_color != "All"
            and str(
                product.get("color")
                or ""
            ).strip()
            != selected_color
        ):

            continue

        # Origin
        if (
            selected_origin != "All"
            and str(
                product.get("origin")
                or ""
            ).strip()
            != selected_origin
        ):

            continue

        filtered_products.append(
            product
        )

    # ========================================================
    # SORT
    # ========================================================

    if sort_option == "Leather ID":

        filtered_products.sort(
            key=lambda x: str(
                x.get("leather_id")
                or ""
            ).casefold()
        )

    elif sort_option == "Article":

        filtered_products.sort(
            key=lambda x: str(
                x.get("article_name")
                or ""
            ).casefold()
        )

    elif sort_option == "Animal":

        filtered_products.sort(
            key=lambda x: str(
                x.get("animal")
                or ""
            ).casefold()
        )

    elif sort_option == "Colour":

        filtered_products.sort(
            key=lambda x: str(
                x.get("color")
                or ""
            ).casefold()
        )

    st.caption(
        f"{len(filtered_products)} "
        f"article(s) found"
    )

    st.divider()

    # ========================================================
    # PRODUCT GRID
    # ========================================================

    if not filtered_products:

        st.info(
            "No leather articles match your search."
        )

        return

    cards_per_row = 3

    for row_start in range(
        0,
        len(filtered_products),
        cards_per_row,
    ):

        row_products = filtered_products[
            row_start:
            row_start + cards_per_row
        ]

        columns = st.columns(
            cards_per_row,
            gap="large",
        )

        for column, product in zip(
            columns,
            row_products,
        ):

            with column:

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

                main_url = get_image_url(
                    product.get(
                        "main_photo"
                    )
                )

                closeup_url = get_image_url(
                    product.get(
                        "closeup_photo"
                    )
                )

                # --------------------------------------------
                # IMAGE
                # --------------------------------------------

                if main_url or closeup_url:

                    render_image_slider(
                        main_url,
                        closeup_url,
                        height=320,
                    )

                else:

                    st.markdown(
                        """
                        <div style="
                            height:320px;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            border-radius:12px;
                            background:#f5f5f5;
                            color:#888;
                        ">
                            No Image
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # --------------------------------------------
                # INFORMATION
                # --------------------------------------------

                st.markdown(
                    f"### {html.escape(article_name)}"
                )

                st.caption(
                    f"Leather ID: {html.escape(leather_id)}"
                )

                info_html = f"""
                <div style="
                    font-size:14px;
                    line-height:1.7;
                ">

                    <b>Colour:</b>
                    {html.escape(
                        str(
                            product.get("color")
                            or "-"
                        )
                    )}
                    <br>

                    <b>Thickness:</b>
                    {html.escape(
                        str(
                            product.get("thickness")
                            or "-"
                        )
                    )}
                    <br>

                    <b>Animal:</b>
                    {html.escape(
                        str(
                            product.get("animal")
                            or "-"
                        )
                    )}
                    <br>

                    <b>Tannage:</b>
                    {html.escape(
                        str(
                            product.get("tannage")
                            or "-"
                        )
                    )}
                    <br>

                    <b>Origin:</b>
                    {html.escape(
                        str(
                            product.get("origin")
                            or "-"
                        )
                    )}

                </div>
                """

                st.markdown(
                    info_html,
                    unsafe_allow_html=True,
                )

                st.write("")

                if st.button(
                    "View Details",
                    width="stretch",
                    key=f"view_{leather_id}",
                ):

                    show_product_details(
                        product
                    )

                st.write("")


# ============================================================
# APP ROUTING
# ============================================================

if "show_admin_login" not in st.session_state:
    st.session_state.show_admin_login = False


# ============================================================
# ADMIN MODE
# ============================================================

if st.session_state.show_admin_login:

    # Back to catalogue
    if st.button(
        "← Back to Catalogue",
        key="back_to_catalogue",
    ):

        st.session_state.show_admin_login = False
        st.session_state.admin_authenticated = False

        st.rerun()

    st.divider()

    if check_admin_password():

        render_admin_panel()

# ============================================================
# CUSTOMER MODE
# ============================================================

else:

    render_catalogue()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Bhartiya Fashions • Leather Catalogue"
)
