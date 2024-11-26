import pyshark
import os
import sys
from datetime import datetime
import glob
import tkinter as tk
from tkinter import filedialog, messagebox
from tqdm import tqdm

def select_directory(prompt):
    """Show directory selection dialog and return selected path"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    directory = filedialog.askdirectory(title=prompt)
    return directory

def count_packets(file_path):
    """Count total SIP packets in file"""
    try:
        capture = pyshark.FileCapture(
            file_path,
            display_filter='sip',
            keep_packets=False,
            output_file=None
        )
        count = 0
        for _ in capture:
            count += 1
        capture.close()
        return count
    except:
        return 0

def extract_sip_info(file_path, output_file):
    try:
        # First count total packets for progress bar
        print("Counting packets...")
        total_packets = count_packets(file_path)
        
        # Create capture object for SIP packets
        capture = pyshark.FileCapture(
            file_path,
            display_filter='sip',
            keep_packets=False,
            output_file=None
        )
        
        print(f"\nProcessing SIP messages in '{file_path}'...")
        
        # Initialize counters
        register_count = 0
        invite_count = 0
        pani_register_count = 0  # P-Access-Network-Info in REGISTER
        pani_invite_count = 0    # P-Access-Network-Info in INVITE
        cni_register_count = 0   # Cellular-Network-Info in REGISTER
        cni_invite_count = 0     # Cellular-Network-Info in INVITE
        
        # Temporary file for storing message details
        temp_file = output_file + '.temp'
        
        # Process packets and write to temporary file
        with open(temp_file, 'w') as file:
            file.write("Detailed SIP Message Information:\n")
            file.write("=" * 50 + "\n")
            
            # Create progress bar
            with tqdm(total=total_packets, desc="Analyzing packets", unit="packet") as pbar:
                for packet in capture:
                    try:
                        if 'SIP' in packet:
                            # Check for REGISTER or INVITE messages
                            message_type = None
                            if hasattr(packet.sip, 'request_method'):
                                if packet.sip.request_method == "REGISTER":
                                    message_type = "REGISTER"
                                    register_count += 1
                                elif packet.sip.request_method == "INVITE":
                                    message_type = "INVITE"
                                    invite_count += 1
                            elif hasattr(packet.sip, 'request_line'):
                                if "REGISTER" in packet.sip.request_line:
                                    message_type = "REGISTER"
                                    register_count += 1
                                elif "INVITE" in packet.sip.request_line:
                                    message_type = "INVITE"
                                    invite_count += 1
                            
                            if message_type:
                                sip_headers = packet.sip
                                
                                # Track header availability based on message type
                                if hasattr(sip_headers, 'p_access_network_info'):
                                    if message_type == "REGISTER":
                                        pani_register_count += 1
                                    elif message_type == "INVITE":
                                        pani_invite_count += 1

                                if hasattr(sip_headers, 'cellular_network_info'):
                                    if message_type == "REGISTER":
                                        cni_register_count += 1
                                    elif message_type == "INVITE":
                                        cni_invite_count += 1
                                
                                # Write message type and timestamp
                                timestamp = packet.sniff_time.strftime('%Y-%m-%d %H:%M:%S.%f')
                                file.write(f"\nMessage Type: {message_type}\n")
                                file.write(f"Timestamp: {timestamp}\n")
                                
                                # Extract To header
                                if hasattr(sip_headers, 'to'):
                                    to_header = sip_headers.to
                                    file.write(f"To: {to_header}\n")
                                    if ';' in to_header:
                                        file.write("To Header Parameters:\n")
                                        params = to_header.split(';')[1:]
                                        for param in params:
                                            param = param.strip()
                                            if '=' in param:
                                                key, value = param.split('=', 1)
                                                file.write(f"  {key.strip()}: {value.strip()}\n")
                                            else:
                                                file.write(f"  {param}\n")
                                
                                # Extract From header
                                if hasattr(sip_headers, 'from_'):
                                    from_header = sip_headers.from_
                                    file.write(f"From: {from_header}\n")
                                    if ';' in from_header:
                                        file.write("From Header Parameters:\n")
                                        params = from_header.split(';')[1:]
                                        for param in params:
                                            param = param.strip()
                                            if '=' in param:
                                                key, value = param.split('=', 1)
                                                file.write(f"  {key.strip()}: {value.strip()}\n")
                                            else:
                                                file.write(f"  {param}\n")

                                # Extract Route header
                                if hasattr(sip_headers, 'route'):
                                    route_header = sip_headers.route
                                    file.write(f"Route: {route_header}\n")

                                    '''
                                    if ';' in route_header:
                                        file.write("Route Header Parameters:\n")
                                        params = route_header.split(';')[1:]
                                        for param in params:
                                            param = param.strip()
                                            if '=' in param:
                                                key, value = param.split('=', 1)
                                                file.write(f"  {key.strip()}: {value.strip()}\n")
                                            else:
                                                file.write(f"  {param}\n")
                                    '''

                                # Extract P-Access-Network-Info
                                if hasattr(sip_headers, 'p_access_network_info'):
                                    p_access_network_info = sip_headers.p_access_network_info
                                    file.write(f"P-Access-Network-Info: {p_access_network_info}\n")
                                                                        
                                    '''
                                    file.write("P-Access-Network-Info Parameters:\n")
                                    for param in p_access_network_info.split(";"):
                                        param = param.strip()
                                        if '=' in param:
                                            key, value = param.split('=', 1)
                                            file.write(f"  {key.strip()}: {value.strip()}\n")
                                        else:
                                            file.write(f"  {param}\n")
                                    '''
                                
                                # Extract Cellular-Network-Info
                                if hasattr(sip_headers, 'cellular_network_info'):
                                    cellular_network_info = sip_headers.cellular_network_info
                                    file.write(f"Cellular-Network-Info: {cellular_network_info}\n")

                                    '''
                                    file.write("Cellular-Network-Info Parameters:\n")
                                    for param in cellular_network_info.split(";"):
                                        param = param.strip()
                                        if '=' in param:
                                            key, value = param.split('=', 1)
                                            file.write(f"  {key.strip()}: {value.strip()}\n")
                                        else:
                                            file.write(f"  {param}\n")
                                    '''
                                
                                file.write("-" * 50 + "\n")

                    except AttributeError as e:
                        print(f"\nSkipping packet due to missing attribute: {str(e)}")
                        continue
                    except Exception as e:
                        print(f"\nError processing packet: {str(e)}")
                        continue
                    finally:
                        pbar.update(1)

        # Write final file with summary at top
        with open(output_file, 'w') as final_file:
            # Write summary
            final_file.write("SIP Analysis Summary\n")
            final_file.write("=" * 50 + "\n")
            final_file.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            final_file.write(f"Input File: {os.path.basename(file_path)}\n")
            final_file.write(f"Total SIP Packets: {total_packets}\n")
            final_file.write(f"REGISTER Messages: {register_count}\n")
            final_file.write(f"INVITE Messages: {invite_count}\n")
            final_file.write("\nHeader Availability:\n")
            final_file.write(f"P-Access-Network-Info in REGISTER: {pani_register_count}\n")
            final_file.write(f"P-Access-Network-Info in INVITE: {pani_invite_count}\n")
            final_file.write(f"Cellular-Network-Info in REGISTER: {cni_register_count}\n")
            final_file.write(f"Cellular-Network-Info in INVITE: {cni_invite_count}\n")
            final_file.write("=" * 50 + "\n\n")
            
            # Copy content from temporary file
            with open(temp_file, 'r') as temp:
                final_file.write(temp.read())
        
        # Remove temporary file
        os.remove(temp_file)

        print(f"\nSummary:")
        print(f"Total packets processed: {total_packets}")
        print(f"REGISTER messages found: {register_count}")
        print(f"INVITE messages found: {invite_count}")
        print(f"\nHeader Availability:")
        print(f"P-Access-Network-Info in REGISTER: {pani_register_count}")
        print(f"P-Access-Network-Info in INVITE: {pani_invite_count}")
        print(f"Cellular-Network-Info in REGISTER: {cni_register_count}")
        print(f"Cellular-Network-Info in INVITE: {cni_invite_count}")

    except pyshark.capture.capture.TSharkCrashException as e:
        print(f"TShark crashed: {str(e)}")
        print("Please ensure you have the latest version of TShark installed")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)
    finally:
        try:
            capture.close()
        except:
            pass

def main():
    # Prompt for traces directory
    traces_dir = select_directory("Select the directory containing PCAP files")
    if not traces_dir:
        messagebox.showerror("Error", "No traces directory selected!")
        sys.exit(1)

    # Prompt for output directory
    output_dir = select_directory("Select the output directory for analysis files")
    if not output_dir:
        messagebox.showerror("Error", "No output directory selected!")
        sys.exit(1)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get all pcap files from traces directory
    pcap_files = glob.glob(os.path.join(traces_dir, '*.pcap'))
    if not pcap_files:
        messagebox.showerror("Error", f"No .pcap files found in '{traces_dir}'!")
        sys.exit(1)

    # Process each pcap file with overall progress bar
    with tqdm(total=len(pcap_files), desc="Processing files", unit="file") as pbar:
        for pcap_file in pcap_files:
            # Generate output filename
            base_name = os.path.basename(pcap_file)
            output_file = os.path.join(output_dir, base_name.replace('.pcap', '.txt'))
            
            print(f"\nProcessing: {base_name}")
            extract_sip_info(pcap_file, output_file)
            print(f"Results saved in '{output_file}'")
            pbar.update(1)

    messagebox.showinfo("Success", "All files processed successfully!")

if __name__ == "__main__":
    main()