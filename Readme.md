# **AWTRIX AutoScheduler**  

This script automatically loads apps from the `apps` folder and sends the defined payloads to AWTRIX.  

## **Prerequisites**  

- Python 3.x  
- Virtual environment (recommended)  
- Dependencies from `requirements.txt`  
- `.env` file with the required environment variables  

## **Installation**  

1. Clone the repository:  

    ```sh
    git clone <repository-url>
    cd <repository-name>
    ```

2. Create and activate a virtual environment:  

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:  

    ```sh
    pip install -r requirements.txt
    ```

4. Create a `.env` file in the root directory and add the following entries:  

    ```ini
    AWTRIX_IP=<IP address of your AWTRIX>
    ```

## **Usage**  

1. Start the script:  

    ```sh
    python awtrix_autoScheduler.py
    ```

2. The script will immediately perform an update and then start a scheduler that runs updates every 10 minutes.  

3. You can manually trigger an update or exit the script by entering the following commands in the console:  
    - `u`: Manually trigger an update  
    - `q`: Quit the script  

## **Structure**  

- [`awtrix_autoScheduler.py`](./awtrix_autoScheduler.py): The main script that starts the scheduler and manages updates.  
- [`apps`](./apps): Directory containing individual app modules.  
- [`.env`](./.env): File containing necessary environment variables.  
- [`requirements.txt`](./requirements.txt): List of required Python dependencies.  

## **Features**  

### [`awtrix_autoScheduler.py`](awtrix_autoScheduler.py)  

- `send_to_awtrix(payload, app_name)`: Sends the payload to the specified AWTRIX IP.  
- `update_awtrix_apps()`: Updates all apps by retrieving payloads from the modules and sending them to AWTRIX.  
- `scheduler_thread()`: Starts the scheduler in a separate thread.  
- `main()`: Main function that controls the script.  

## **License**  

This project is licensed under the MIT License. See the LICENSE file for details.  
