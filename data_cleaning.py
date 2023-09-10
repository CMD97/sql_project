from data_extraction import DataExtractor
from database_utils import DatabaseConnector
import pandas as pd
import re
import numpy as np

class DataCleaning:
    def __init__(self):
        de = DataExtractor()   # Initialising the DataExtractor class to begin the process of cleaning.

        # Cleaning of users in the sales data.
        # self.users_df = de.df_rds_table
        # self.clean_data = self.clean_user_data()

        # Cleaning of the card details in the sales data.
        # self.card_df = de.card_details_df
        # self.clean_card_df = self.clean_card_data()

        # Cleaning of the store details in the sales data.
        self.store_data_df = de.store_details_df
        self.clean_store_df = self.clean_store_data()
        # print(self.clean_store_df)

        # Uploading to the SQL database which is taken in within the database_utils file.
        dc = DatabaseConnector
        dc().upload_to_db(self.clean_store_df)

    def clean_user_data(self):
        # Dropping duplicates & null values
        cleaning_users_df = self.users_df.dropna()
        cleaning_users_df = cleaning_users_df.drop_duplicates()

        # Dropping the "index" column that's taken through to pgAdmin4
        cleaning_users_df.drop("index", axis=1, inplace=True)
        
        # Setting required types to category
        cleaning_users_df['country'] = cleaning_users_df['country'].astype('category')
        cleaning_users_df['country_code'] = cleaning_users_df['country_code'].astype('category')

        # Ensuring data which has a `country code` of the specified country has the corresponding country in the `country` column.
        cleaning_users_df.loc[cleaning_users_df['country_code'] == 'DE', 'country'] = 'Germany'
        cleaning_users_df.loc[cleaning_users_df['country'] == 'Germany', 'country_code'] = 'DE'

        cleaning_users_df.loc[cleaning_users_df['country_code'] == 'GB', 'country'] = 'United Kingdom'
        cleaning_users_df.loc[cleaning_users_df['country'] == 'United Kingdom', 'country_code'] = 'GB'

        cleaning_users_df.loc[cleaning_users_df['country_code'] == 'US', 'country'] = 'United States'
        cleaning_users_df.loc[cleaning_users_df['country'] == 'United States', 'country_code'] = 'US'

        # Dropping rows that do not have a country code as DE/GB/US - in turn dropping other NULL values
        incorrect_rows_with_wrong_country_codes = ~cleaning_users_df['country_code'].isin(['US','GB','DE'])
        cleaning_users_df = cleaning_users_df[~incorrect_rows_with_wrong_country_codes]

        # Phone Number formatting done in a different function
        cleaning_users_df['phone_number'] = cleaning_users_df['phone_number'].apply(self.standardise_phone_number)
        
        # Setting required columns to timedate
        cleaning_users_df['date_of_birth'] = pd.to_datetime(cleaning_users_df['date_of_birth'], errors='coerce').dt.date
        cleaning_users_df['join_date'] = pd.to_datetime(cleaning_users_df['join_date'], errors='coerce').dt.date

        return cleaning_users_df

    def standardise_phone_number(self, phone_number):                       # standardising phone numbers --- improvements to be made upon the phone_number

        # Regex to get all rows present with only numbers                       
        numbers_only_pattern = re.compile(r'\d+')
        matches = re.finditer(numbers_only_pattern, phone_number)
        cleaned_numbers = ''.join(match.group() for match in matches)

        # Regex to remove the `001` out of a US phone number
        US_cleaning_pattern = re.compile(r"^(0+)?1(\d{10})\b")
        match = re.match(US_cleaning_pattern, cleaned_numbers)
        if match:
            cleaned_numbers = match.group(2)
            return cleaned_numbers
        else:
            return cleaned_numbers
    
    # Cleaning the card details data
    def clean_card_data(self):

        # Taking the card details from the init method into the function, dropping NaN rows & duplicates.
        cleaning_card_df = self.card_df.dropna()
        cleaning_card_df = cleaning_card_df.drop_duplicates()
        
        # Using a regex on the expiry date to check for null values and dropping them.
        expiry_date_pattern = re.compile(r"\d{2}\/\d{2}")
        rows_with_incorrect_expiry = ~cleaning_card_df['expiry_date'].str.contains(expiry_date_pattern)
        cleaning_card_df = cleaning_card_df[~rows_with_incorrect_expiry]

        # Changing expiry dates to be the last day of the month as they usually will be and changing to date dtype.
        cleaning_card_df['expiry_date'] = cleaning_card_df['expiry_date'].apply(self.convert_expiry_date)

        # Changing the payment date confirmed dtype to a date dtype.
        cleaning_card_df['date_payment_confirmed'] = pd.to_datetime(cleaning_card_df['date_payment_confirmed'], format='%Y-%m-%d', errors='coerce').dt.date

        return cleaning_card_df

    def convert_expiry_date(self, expiry_date):
        month, expiry_year = expiry_date.split('/')
        expiry_year = '20' + expiry_year # Expiry dates will only be present for the expiry_year `2000+` hence `20 + expiry_year`
        date_object = pd.Timestamp(f'{expiry_year}-{month}-01') + pd.DateOffset(months=1, days=-1)
        return date_object.date()
    
    def clean_store_data(self):
        cleaning_store_data_df = self.store_data_df.copy()

        # Dropping the column `lat` as it carries all [null] values.
        cleaning_store_data_df.drop('lat', axis=1, inplace=True)
        # Dropping the index row taken through to pgAdmin4.
        cleaning_store_data_df.drop('index', axis=1, inplace=True)

        # Dropping rows that are incorrect, 14 in total.
        incorrect_rows_with_wrong_country_codes = ~cleaning_store_data_df['country_code'].isin(['US','GB','DE'])
        cleaning_store_data_df = cleaning_store_data_df[~incorrect_rows_with_wrong_country_codes]

        # Using a regex to ensure staff_numbers now has only numbers inside
        cleaning_store_data_df['staff_numbers'] = cleaning_store_data_df['staff_numbers'].apply(self.staff_numbers_regex)

        # Ensuring data which has a `country code` of the specified country has the corresponding continent in the `contient` column.
        cleaning_store_data_df.loc[(cleaning_store_data_df['country_code'] == 'DE') | (cleaning_store_data_df['country_code'] == 'GB'), 'continent'] = 'Europe'
        cleaning_store_data_df.loc[cleaning_store_data_df['country_code'] == 'US', 'continent'] = 'America'

        # Getting values labelled `N/A` to be set as NaN
        cleaning_store_data_df['longitude'] = pd.to_numeric(cleaning_store_data_df['longitude'], errors='coerce')
        cleaning_store_data_df['latitude'] = pd.to_numeric(cleaning_store_data_df['latitude'], errors='coerce')

        # Changing datatype of a column to the correct datatype.
        cleaning_store_data_df['longitude'] = cleaning_store_data_df['longitude'].astype(float)
        cleaning_store_data_df['latitude'] = cleaning_store_data_df['latitude'].astype(float)
        cleaning_store_data_df['staff_numbers'] = cleaning_store_data_df['staff_numbers'].astype('int32')
        cleaning_store_data_df['store_type'] = cleaning_store_data_df['store_type'].astype('category')
        cleaning_store_data_df['country_code'] = cleaning_store_data_df['country_code'].astype('category')

        # Setting opening_date column to be the correct datatype.
        cleaning_store_data_df['opening_date'] = pd.to_datetime(cleaning_store_data_df['opening_date'], errors='coerce').dt.date

        # Reordering columns
        new_column_order = ['store_code', 'store_type', 'address', 'locality', 'longitude', 'latitude', 'country_code', 'continent', 'staff_numbers', 'opening_date']
        cleaning_store_data_df = cleaning_store_data_df[new_column_order]

        # Renaming locality to location
        cleaning_store_data_df.rename(columns={'locality': 'location'}, inplace=True)

        return cleaning_store_data_df
    # Function to get all rows present with only numbers  
    def staff_numbers_regex(self, staff_numbers):                       
        discarding_letters_pattern = re.compile(r'\d+')
        matches = re.finditer(discarding_letters_pattern, staff_numbers)
        cleaned_numbers = ''.join(match.group() for match in matches)
        return cleaned_numbers
    
        
    


if __name__ == '__main__':
    DataCleaning()