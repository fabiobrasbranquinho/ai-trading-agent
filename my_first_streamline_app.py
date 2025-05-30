# Suggested filename: my_first_streamlit_app.py

import streamlit as st # 'st' is the standard alias for streamlit

def main():
    st.title("My First Streamlit App!")

    st.header("This is a header")
    st.subheader("And this is a subheader")

    st.write("Hello, Streamlit World! This is just plain text.")
    st.markdown("---") # Adds a horizontal line

    # Simple interactive widget: Text Input
    name = st.text_input("What's your name?", placeholder="Enter your name here")

    if name: # Only display if a name has been entered
        st.write(f"Hello, {name}! Welcome to Streamlit.")
    
    st.markdown("---")

    # Another interactive widget: Button
    if st.button("Click Me!"):
        st.balloons() # A fun little Streamlit feature!
        st.success("You clicked the button! 🎉 Hooray!")
        st.write("Streamlit makes creating interactive elements easy.")

if __name__ == '__main__':
    main()