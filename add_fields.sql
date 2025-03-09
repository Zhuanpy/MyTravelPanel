ALTER TABLE visa_documents
ADD COLUMN common_document_info TEXT AFTER singapore_identity,
ADD COLUMN specific_document_info TEXT AFTER common_document_info; 