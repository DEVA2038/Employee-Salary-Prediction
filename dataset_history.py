# dataset_history.py - Dataset History Management

import os
from pathlib import Path
from datetime import datetime
import json
from sqlalchemy.orm import Session
from database import get_db, CompanyRequest, CompanyDataset
import logging

logger = logging.getLogger(__name__)

class DatasetHistoryManager:
    def __init__(self, upload_folder, company_models_folder):
        self.upload_folder = Path(upload_folder)
        self.company_models_folder = Path(company_models_folder)
        
    def get_company_datasets(self, company_name):
        """Get all datasets for a company"""
        try:
            db: Session = next(get_db())
            
            # Get company request
            company_request = db.query(CompanyRequest).filter(
                CompanyRequest.company_name == company_name
            ).first()
            
            if not company_request:
                return []
            
            # Get all datasets for this company
            datasets = []
            
            # Original dataset
            if company_request.dataset_filename:
                original_path = self.upload_folder / company_request.dataset_filename
                if original_path.exists():
                    datasets.append({
                        'id': f"original_{company_request.id}",
                        'filename': company_request.dataset_filename,
                        'size': original_path.stat().st_size,
                        'upload_date': company_request.created_at,
                        'records': company_request.data_points or 0,
                        'is_active': True,
                        'type': 'original'
                    })
            
            # Check for retrained datasets
            retrain_pattern = f"{company_name.replace(' ', '_')}_retrain_*.csv"
            for retrain_file in self.upload_folder.glob(retrain_pattern):
                try:
                    # Try to get record count
                    import pandas as pd
                    df = pd.read_csv(retrain_file)
                    records = len(df)
                except:
                    records = 0
                
                # Check if this is the active model
                is_active = False
                if company_request.model_filename:
                    model_name = Path(company_request.model_filename).stem
                    retrain_name = retrain_file.stem
                    if retrain_name in model_name:
                        is_active = True
                
                datasets.append({
                    'id': f"retrain_{retrain_file.stem}",
                    'filename': retrain_file.name,
                    'size': retrain_file.stat().st_size,
                    'upload_date': datetime.fromtimestamp(retrain_file.stat().st_mtime),
                    'records': records,
                    'is_active': is_active,
                    'type': 'retrain'
                })
            
            # Sort by upload date (newest first)
            datasets.sort(key=lambda x: x['upload_date'], reverse=True)
            return datasets
            
        except Exception as e:
            logger.error(f"Error getting company datasets: {e}")
            return []
    
    def download_dataset(self, company_name, dataset_id):
        """Download a specific dataset"""
        try:
            if dataset_id.startswith('original_'):
                # Original dataset
                db: Session = next(get_db())
                company_request = db.query(CompanyRequest).filter(
                    CompanyRequest.company_name == company_name
                ).first()
                
                if not company_request or not company_request.dataset_filename:
                    return None
                
                file_path = self.upload_folder / company_request.dataset_filename
                
            elif dataset_id.startswith('retrain_'):
                # Retrain dataset
                retrain_id = dataset_id.replace('retrain_', '')
                retrain_pattern = f"{company_name.replace(' ', '_')}_retrain_*.csv"
                
                for retrain_file in self.upload_folder.glob(retrain_pattern):
                    if retrain_id in retrain_file.stem:
                        file_path = retrain_file
                        break
                else:
                    return None
            else:
                return None
            
            if file_path and file_path.exists():
                return file_path
                
        except Exception as e:
            logger.error(f"Error locating dataset: {e}")
        
        return None

# Initialize dataset history manager
from config import UPLOAD_FOLDER, COMPANY_MODELS_FOLDER
dataset_manager = DatasetHistoryManager(UPLOAD_FOLDER, COMPANY_MODELS_FOLDER)