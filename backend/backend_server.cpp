// SparkLabs Backend Server
// A lightweight HTTP server for SparkLabs AI-Native Game Engine

#include <iostream>
#include <string>
#include <thread>
#include <vector>
#include <cstring>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define PORT 8081
#define BUFFER_SIZE 4096

// SparkLabs Engine Status
struct SparkLabsStatus {
    bool engineReady;
    bool aiRuntimeReady;
    bool neuralRendererReady;
    int activeSessions;
    std::string version;
};

SparkLabsStatus g_status = {
    true,   // engineReady
    true,   // aiRuntimeReady
    true,   // neuralRendererReady
    0,      // activeSessions
    "1.0.0" // version
};

// Generate SparkLabs API response
std::string generateStatusJSON() {
    return "{"
           "\"status\":\"ok\","
           "\"engine\":\"SparkLabs AI-Native Game Engine\","
           "\"version\":\"" + g_status.version + "\","
           "\"engineReady\":" + std::string(g_status.engineReady ? "true" : "false") + ","
           "\"aiRuntimeReady\":" + std::string(g_status.aiRuntimeReady ? "true" : "false") + ","
           "\"neuralRendererReady\":" + std::string(g_status.neuralRendererReady ? "true" : "false") + ","
           "\"activeSessions\":" + std::to_string(g_status.activeSessions) +
           "}";
}

std::string generateCORSHeaders() {
    return "Access-Control-Allow-Origin: *\r\n"
           "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
           "Access-Control-Allow-Headers: Content-Type\r\n";
}

void handleClient(int clientSocket) {
    char buffer[BUFFER_SIZE];
    int bytesRead = recv(clientSocket, buffer, BUFFER_SIZE - 1, 0);
    
    if (bytesRead > 0) {
        buffer[bytesRead] = '\0';
        std::string request(buffer);
        
        std::string response;
        
        if (request.find("OPTIONS") == 0) {
            response = "HTTP/1.1 204 No Content\r\n" +
                      generateCORSHeaders() +
                      "Content-Length: 0\r\n"
                      "Connection: close\r\n\r\n";
        }
        else if (request.find("GET /api/status") != std::string::npos) {
            std::string jsonBody = generateStatusJSON();
            response = "HTTP/1.1 200 OK\r\n" +
                      generateCORSHeaders() +
                      "Content-Type: application/json\r\n"
                      "Content-Length: " + std::to_string(jsonBody.length()) + "\r\n"
                      "Connection: close\r\n\r\n" +
                      jsonBody;
        }
        else if (request.find("GET /api/features") != std::string::npos) {
            std::string jsonBody = "{"
                "\"features\":["
                "{\"name\":\"AI-Native Content Generation\",\"status\":\"active\"},"
                "{\"name\":\"Neural Rendering\",\"status\":\"active\"},"
                "{\"name\":\"AI Agent System\",\"status\":\"active\"},"
                "{\"name\":\"World Model Architecture\",\"status\":\"active\"},"
                "{\"name\":\"Real-Time Generation\",\"status\":\"active\"}"
                "]}";
            response = "HTTP/1.1 200 OK\r\n" +
                      generateCORSHeaders() +
                      "Content-Type: application/json\r\n"
                      "Content-Length: " + std::to_string(jsonBody.length()) + "\r\n"
                      "Connection: close\r\n\r\n" +
                      jsonBody;
        }
        else {
            std::string htmlBody = "<html><body><h1>SparkLabs Backend Server</h1><p>AI-Native Game Engine API Server is running.</p></body></html>";
            response = "HTTP/1.1 200 OK\r\n" +
                      generateCORSHeaders() +
                      "Content-Type: text/html\r\n"
                      "Content-Length: " + std::to_string(htmlBody.length()) + "\r\n"
                      "Connection: close\r\n\r\n" +
                      htmlBody;
        }
        
        send(clientSocket, response.c_str(), response.length(), 0);
    }
    
    close(clientSocket);
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "  SparkLabs Backend Server" << std::endl;
    std::cout << "  AI-Native Game Engine" << std::endl;
    std::cout << "  Version 1.0.0" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    
    int serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (serverSocket < 0) {
        std::cerr << "Failed to create socket" << std::endl;
        return 1;
    }
    
    int opt = 1;
    setsockopt(serverSocket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    
    struct sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(PORT);
    
    if (bind(serverSocket, (struct sockaddr*)&serverAddr, sizeof(serverAddr)) < 0) {
        std::cerr << "Failed to bind to port " << PORT << std::endl;
        close(serverSocket);
        return 1;
    }
    
    if (listen(serverSocket, 10) < 0) {
        std::cerr << "Failed to listen on socket" << std::endl;
        close(serverSocket);
        return 1;
    }
    
    std::cout << "SparkLabs Backend Server started on http://localhost:" << PORT << std::endl;
    std::cout << "API Endpoints:" << std::endl;
    std::cout << "  - GET /api/status   - Engine status" << std::endl;
    std::cout << "  - GET /api/features - Available features" << std::endl;
    std::cout << std::endl;
    std::cout << "Press Ctrl+C to stop the server" << std::endl;
    std::cout << std::endl;
    
    while (true) {
        struct sockaddr_in clientAddr;
        socklen_t clientLen = sizeof(clientAddr);
        
        int clientSocket = accept(serverSocket, (struct sockaddr*)&clientAddr, &clientLen);
        if (clientSocket < 0) {
            continue;
        }
        
        std::thread clientThread(handleClient, clientSocket);
        clientThread.detach();
    }
    
    close(serverSocket);
    return 0;
}
