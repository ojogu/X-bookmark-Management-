from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

# Mock Frontend Endpoints
#API endpoint
url = "https://4mlncfwr-5000.uks1.devtunnels.ms/api/v1"
@app.get("/", response_class=HTMLResponse)
async def home_page():
    return """
    <html>
        <body>
            <h1>My App - Home</h1>
            <a href="/login">
                <button>Sign in with Twitter</button>
            </a>
        </body>
    </html>
    """

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    # Call your backend to get OAuth URL
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{url}/auth/login")

            if response.status_code == 200:
                data = response.json()
                oauth_url = data.get("url")

                if oauth_url:
                    return f"""
                    <html>
                        <body>
                            <h1>Redirecting to Twitter...</h1>
                            <script>
                                window.location.href = "{oauth_url}";
                            </script>
                            <p>If not redirected, <a href="{oauth_url}">click here</a></p>
                        </body>
                    </html>
                    """
                else:
                    return f"""
                    <html>
                        <body>
                            <h1>Login Error</h1>
                            <p>Invalid response from server: missing OAuth URL</p>
                            <a href="/">Go back</a>
                        </body>
                    </html>
                    """
            else:
                # Handle error responses
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", f"HTTP {response.status_code}")
                except:
                    error_message = f"HTTP {response.status_code}: {response.text[:100]}"

                return f"""
                <html>
                    <body>
                        <h1>Login Error</h1>
                        <p>{error_message}</p>
                        <a href="/">Go back</a>
                    </body>
                </html>
                """

        except httpx.ConnectError as e:
            return f"""
            <html>
                <body>
                    <h1>Login Error</h1>
                    <p>Failed to connect to authentication service. Please try again later.</p>
                    <a href="/">Go back</a>
                </body>
            </html>
            """
        except httpx.TimeoutException as e:
            return f"""
            <html>
                <body>
                    <h1>Login Error</h1>
                    <p>Request timed out. Please try again.</p>
                    <a href="/">Go back</a>
                </body>
            </html>
            """
        except Exception as e:
            return f"""
            <html>
                <body>
                    <h1>Login Error</h1>
                    <p>An unexpected error occurred: {str(e)[:100]}</p>
                    <a href="/">Go back</a>
                </body>
            </html>
            """

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Extract JWT token from URL parameter
    access_token = request.query_params.get("access-token")
    refresh_token = request.query_params.get("refresh-token")
    error = request.query_params.get("error")
    
    if error:
        return f"""
        <html>
            <body>
                <h1>Authentication Failed</h1>
                <p>Error: {error}</p>
                <a href="/">Try again</a>
            </body>
        </html>
        """
    
    if not access_token:
        return """
        <html>
            <body>
                <h1>Access Denied</h1>
                <p>No authentication token found</p>
                <a href="/">Login</a>
            </body>
        </html>
        """
    
    return f"""
    <html>
        <body>
            <h1>Welcome to Dashboard!</h1>
            <p><strong>You are logged in!</strong></p>
            <p>Your JWT access token: <code>{access_token}...</code></p>
            <p>Your JWT refresh token: <code>{refresh_token}...</code></p>
            
            <h3>Available Actions:</h3>
            <button onclick="makeApiCall()">Test API Call</button>
            <button onclick="logout()">Logout</button>
            
            <div id="api-result"></div>
            
            <script>
                // Store token in localStorage for future API calls
                localStorage.setItem('jwt_token', '{access_token}');
                
                // Clean URL (remove token from address bar)
                window.history.replaceState({{}}, document.title, "/dashboard");
                
                async function makeApiCall() {{
                    try {{
                        const response = await fetch('https://257b46155a88.ngrok-free.app/api/user-data', {{
                            headers: {{
                                'Authorization': 'Bearer ' + localStorage.getItem('jwt_token')
                            }}
                        }});
                        
                        if (response.status === 401) {{
                            alert('Token expired! Please login again.');
                            logout();
                            return;
                        }}
                        
                        const data = await response.json();
                        document.getElementById('api-result').innerHTML = 
                            '<h4>API Response:</h4><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    }} catch (error) {{
                        document.getElementById('api-result').innerHTML = 
                            '<h4>API Error:</h4><p>' + error.message + '</p>';
                    }}
                }}
                
                function logout() {{
                    localStorage.removeItem('jwt_token');
                    window.location.href = '/';
                }}
            </script>
        </body>
    </html>
    """

@app.get("/profile", response_class=HTMLResponse)
async def profile_page():
    return """
    <html>
        <body>
            <h1>User Profile</h1>
            <div id="profile-data">Loading...</div>
            <a href="/dashboard">Back to Dashboard</a>
            
            <script>
                async function loadProfile() {
                    const token = localStorage.getItem('jwt_token');
                    
                    if (!token) {
                        document.getElementById('profile-data').innerHTML = 
                            '<p>Not logged in. <a href="/">Login</a></p>';
                        return;
                    }
                    
                    try {
                        const response = await fetch('http://localhost:8000/api/profile', {
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (response.status === 401) {
                            document.getElementById('profile-data').innerHTML = 
                                '<p>Session expired. <a href="/">Login again</a></p>';
                            return;
                        }
                        
                        const data = await response.json();
                        document.getElementById('profile-data').innerHTML = 
                            '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                            
                    } catch (error) {
                        document.getElementById('profile-data').innerHTML = 
                            '<p>Error loading profile: ' + error.message + '</p>';
                    }
                }
                
                loadProfile();
            </script>
        </body>
    </html>
    """

# Run with: uvicorn frontend_mock:app --port 3000
