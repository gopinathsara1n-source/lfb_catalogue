import streamlit as st


st.title("Contact")


st.write(
    "For leather enquiries, please contact us."
)


with st.form("contact_form"):

    name = st.text_input("Name")

    company = st.text_input("Company")

    email = st.text_input("Email")

    message = st.text_area("Message")

    submitted = st.form_submit_button(
        "Send Enquiry"
    )


    if submitted:

        if not name or not email or not message:

            st.warning(
                "Please complete the required fields."
            )

        else:

            st.success(
                "Thank you. Your enquiry has been received."
            )
