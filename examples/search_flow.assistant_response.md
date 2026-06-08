After the user enters a keyword and presses Enter, the browser triggers a keydown or form submit event. The frontend captures the event, reads the input value, trims it, and checks whether it is empty.

If the keyword is empty, the frontend stops the request and asks the user to enter a keyword again. If the keyword is valid, the frontend builds a search request with the URL, query parameters, and request options, then sends it to the backend.

The backend parses the query parameters, runs search retrieval and ranking, and returns a JSON response to the frontend.

The frontend parses the response, updates page state, renders the result list, and the user sees the search results page.
